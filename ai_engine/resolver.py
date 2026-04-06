# backend/ai_engine/resolver.py

from groq import Groq
from app.config import GROQ_API_KEY, AI_MODEL

client = Groq(api_key=GROQ_API_KEY)

RESOLVER_SYSTEM_PROMPT = """
You are a helpful, professional IT/HR support agent.
Your job is to write a clear, specific, human-like response to a support ticket.

Rules:
- Address the user's specific issue directly
- Be warm but professional
- Give actionable steps where possible
- Never be generic ("We have received your ticket...")
- Keep response under 200 words
- End with: "Was this helpful? Reply YES or NO."
- Do NOT mention you are an AI
"""

def generate_auto_response(
    title: str,
    body: str,
    category: str,
    summary: str,
    submitter_name: str
) -> str:
    """
    Generates a contextual auto-response for auto-resolvable tickets.
    """

    prompt = f"""
Write a support response for this ticket:

Submitter: {submitter_name}
Category: {category}
Title: {title}
Issue Summary: {summary}
Full Description: {body}

Write a specific, helpful response addressing their exact issue.
"""

    try:
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": RESOLVER_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            max_tokens=400,
            temperature=0.4,
        )
        return response.choices[0].message.content

    except Exception as e:
        print(f"❌ Auto-resolver error: {e}")
        return (
            f"Hi {submitter_name},\n\n"
            f"Thank you for reaching out regarding: {title}.\n"
            f"Our team is reviewing your request and will follow up shortly.\n\n"
            f"Was this helpful? Reply YES or NO."
        )