# backend/ai_engine/router.py

# ─────────────────────────────────────────────
# ROUTING RULES TABLE
# category + severity → department
# ─────────────────────────────────────────────

ROUTING_RULES = {
    # (category, severity) → department
    ("DB", "Critical"):      "Engineering",
    ("DB", "High"):          "Engineering",
    ("DB", "Medium"):        "Engineering",
    ("DB", "Low"):           "Engineering",

    ("Server", "Critical"):  "DevOps",
    ("Server", "High"):      "DevOps",
    ("Server", "Medium"):    "DevOps",
    ("Server", "Low"):       "DevOps",

    ("Bug", "Critical"):     "Engineering",
    ("Bug", "High"):         "Engineering",
    ("Bug", "Medium"):       "Product",
    ("Bug", "Low"):          "Product",

    ("Feature", "Critical"): "Product",
    ("Feature", "High"):     "Product",
    ("Feature", "Medium"):   "Product",
    ("Feature", "Low"):      "Product",

    ("Access", "Critical"):  "IT",
    ("Access", "High"):      "IT",
    ("Access", "Medium"):    "IT",
    ("Access", "Low"):       "IT",

    ("Billing", "Critical"): "Finance",
    ("Billing", "High"):     "Finance",
    ("Billing", "Medium"):   "Finance",
    ("Billing", "Low"):      "Finance",

    ("HR", "Critical"):      "HR",
    ("HR", "High"):          "HR",
    ("HR", "Medium"):        "HR",
    ("HR", "Low"):           "HR",

    ("Other", "Critical"):   "Management",
    ("Other", "High"):       "IT",
    ("Other", "Medium"):     "IT",
    ("Other", "Low"):        "IT",
}

# Fallback if category+severity combo not found
DEFAULT_DEPARTMENT = "IT"


def get_department_for_ticket(category: str, severity: str, ai_suggested: str = "") -> str:
    """
    Returns the correct department name for a ticket.
    Priority: routing rules table → AI suggestion → default
    """
    # 1. Check routing rules first (highest priority)
    key = (category, severity)
    if key in ROUTING_RULES:
        return ROUTING_RULES[key]

    # 2. Fall back to AI suggestion if valid
    valid_departments = [
        "Engineering", "Finance", "HR", "IT",
        "DevOps", "Product", "Legal", "Management"
    ]
    if ai_suggested and ai_suggested in valid_departments:
        return ai_suggested

    # 3. Last resort default
    return DEFAULT_DEPARTMENT


def get_routing_explanation(category: str, severity: str, department: str) -> str:
    """
    Returns a human-readable explanation of why this ticket was routed here.
    """
    return (
        f"Ticket categorized as '{category}' with '{severity}' severity. "
        f"Based on routing rules, this is handled by the {department} department."
    )