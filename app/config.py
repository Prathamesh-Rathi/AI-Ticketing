# backend/app/config.py

GROQ_API_KEY = ""

DATABASE_URL = "sqlite:///./ticketing.db"

APP_NAME = "AI Ticketing System"
APP_VERSION = "1.0.0"

# Updated model name (llama3-8b was decommissioned, use this instead)
AI_MODEL = "llama-3.1-8b-instant"     # Free, fast, still on Groq free tier
AI_MAX_TOKENS = 1024
AI_RETRY_ATTEMPTS = 3

CONFIDENCE_THRESHOLD = 60
ESCALATION_HOURS = 2