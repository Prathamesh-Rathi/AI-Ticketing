# backend/ai_engine/analyzer.py

import json
import re
from groq import Groq
from app.config import GROQ_API_KEY, AI_MODEL, AI_MAX_TOKENS, AI_RETRY_ATTEMPTS, CONFIDENCE_THRESHOLD

client = Groq(api_key=GROQ_API_KEY)

# ─────────────────────────────────────────────
# SYSTEM PROMPT — strict JSON contract
# ─────────────────────────────────────────────

SYSTEM_PROMPT = """
You are an AI ticket analysis engine for an internal IT/HR helpdesk system.

Your job is to analyze support tickets and return ONLY a valid JSON object.
No explanation. No markdown. No extra text. Just raw JSON.

You MUST return this exact JSON structure:
{
  "category": "<one of: Billing | Bug | Access | HR | Server | DB | Feature | Other>",
  "summary": "<2-3 sentence concise summary of the issue>",
  "severity": "<one of: Critical | High | Medium | Low>",
  "resolution_path": "<one of: Auto-resolve | Assign>",
  "sentiment": "<one of: Frustrated | Neutral | Polite>",
  "suggested_department": "<one of: Engineering | Finance | HR | IT | DevOps | Product | Legal | Management>",
  "suggested_employee": "<name if obvious from context, else empty string>",
  "confidence_score": <integer 0-100>,
  "estimated_resolution_time": "<e.g. 30 minutes | 2 hours | 1 day | 3 days>",
  "routing_reason": "<1 sentence explaining why you routed it this way>"
}

Severity rules:
- Critical: system down, data loss, security breach, payroll failure
- High: major feature broken, access blocked for multiple users
- Medium: single user issue, non-urgent bug
- Low: question, feature request, general inquiry

Resolution path rules:
- Auto-resolve: password reset, FAQ, HR policy question, status check, basic billing query
- Assign: anything requiring human investigation, code fix, account changes, legal review

Return ONLY the JSON. Nothing else.
"""

# ─────────────────────────────────────────────
# JSON VALIDATOR
# ─────────────────────────────────────────────

REQUIRED_FIELDS = [
    "category", "summary", "severity", "resolution_path",
    "sentiment", "suggested_department", "confidence_score",
    "estimated_resolution_time", "routing_reason"
]

VALID_CATEGORIES = ["Billing", "Bug", "Access", "HR", "Server", "DB", "Feature", "Other"]
VALID_SEVERITIES = ["Critical", "High", "Medium", "Low"]
VALID_PATHS = ["Auto-resolve", "Assign"]
VALID_SENTIMENTS = ["Frustrated", "Neutral", "Polite"]
VALID_DEPARTMENTS = ["Engineering", "Finance", "HR", "IT", "DevOps", "Product", "Legal", "Management"]

def validate_ai_output(data: dict) -> tuple[bool, str]:
    """
    Returns (is_valid, error_message)
    """
    # Check all required fields exist
    for field in REQUIRED_FIELDS:
        if field not in data:
            return False, f"Missing field: {field}"

    # Validate enum values
    if data["category"] not in VALID_CATEGORIES:
        return False, f"Invalid category: {data['category']}"

    if data["severity"] not in VALID_SEVERITIES:
        return False, f"Invalid severity: {data['severity']}"

    if data["resolution_path"] not in VALID_PATHS:
        return False, f"Invalid resolution_path: {data['resolution_path']}"

    if data["sentiment"] not in VALID_SENTIMENTS:
        return False, f"Invalid sentiment: {data['sentiment']}"

    if data["suggested_department"] not in VALID_DEPARTMENTS:
        return False, f"Invalid department: {data['suggested_department']}"

    # Validate confidence score
    if not isinstance(data["confidence_score"], int):
        try:
            data["confidence_score"] = int(data["confidence_score"])
        except:
            return False, "confidence_score must be an integer"

    if not (0 <= data["confidence_score"] <= 100):
        return False, "confidence_score must be between 0 and 100"

    return True, "ok"


def extract_json(text: str) -> dict:
    """
    Extracts JSON from AI response even if it has extra text around it.
    """
    # Try direct parse first
    try:
        return json.loads(text.strip())
    except:
        pass

    # Try to find JSON block inside the text
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except:
            pass

    raise ValueError("No valid JSON found in AI response")


# ─────────────────────────────────────────────
# MAIN ANALYZER FUNCTION
# ─────────────────────────────────────────────

def analyze_ticket(title: str, body: str) -> dict:
    """
    Sends ticket to Groq, gets structured JSON analysis.
    Retries up to AI_RETRY_ATTEMPTS times if output is invalid.
    Returns final analysis dict.
    """

    user_message = f"""
Analyze this support ticket:

TITLE: {title}

DESCRIPTION:
{body}

Return ONLY the JSON object as specified. No other text.
"""

    last_error = ""

    for attempt in range(1, AI_RETRY_ATTEMPTS + 1):
        print(f"🤖 AI analysis attempt {attempt}/{AI_RETRY_ATTEMPTS}...")

        try:
            response = client.chat.completions.create(
                model=AI_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=AI_MAX_TOKENS,
                temperature=0.1,   # low temperature = consistent structured output
            )

            raw_text = response.choices[0].message.content
            print(f"📝 Raw AI response: {raw_text[:200]}...")

            # Extract and validate JSON
            parsed = extract_json(raw_text)
            is_valid, error = validate_ai_output(parsed)

            if is_valid:
                print(f"✅ AI analysis successful on attempt {attempt}")

                # BONUS: If confidence below threshold, force human assignment
                if parsed["confidence_score"] < CONFIDENCE_THRESHOLD:
                    print(f"⚠️ Low confidence ({parsed['confidence_score']}%), forcing human assignment")
                    parsed["resolution_path"] = "Assign"
                    parsed["routing_reason"] += f" (Low confidence {parsed['confidence_score']}% — forced to human review)"

                return parsed
            else:
                last_error = error
                print(f"❌ Validation failed on attempt {attempt}: {error}")

        except Exception as e:
            last_error = str(e)
            print(f"❌ Error on attempt {attempt}: {e}")

    # All retries failed — return safe fallback
    print(f"🚨 All {AI_RETRY_ATTEMPTS} attempts failed. Using fallback.")
    return {
        "category": "Other",
        "summary": f"Ticket submitted: {title}. Automated analysis failed — requires manual review.",
        "severity": "Medium",
        "resolution_path": "Assign",
        "sentiment": "Neutral",
        "suggested_department": "IT",
        "suggested_employee": "",
        "confidence_score": 0,
        "estimated_resolution_time": "1 day",
        "routing_reason": f"AI analysis failed after {AI_RETRY_ATTEMPTS} attempts: {last_error}"
    }