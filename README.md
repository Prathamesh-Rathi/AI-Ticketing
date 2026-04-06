# ⚡ TicketAI — AI-Powered Internal Ticketing System

A production-ready smart internal ticketing platform where AI reads incoming tickets, decides whether it can auto-resolve them, and if not, routes them to the correct department and assignee.

---

## 🎯 What This System Does

- **AI analyzes every ticket** — category, severity, sentiment, confidence score
- **Auto-resolves simple tickets** — password reset, HR queries, FAQs
- **Routes complex tickets** — to the right department and employee automatically
- **Smart assignment** — scores employees by skill match, load, and availability
- **Full ticket lifecycle** — New → Assigned → In Progress → Pending → Resolved → Closed
- **Escalation engine** — auto-reassigns Critical/High tickets ignored for 2+ hours
- **Similar ticket detection** — finds related resolved tickets while you type
- **Analytics dashboard** — charts for department load, categories, severity, status

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.10 · FastAPI |
| Frontend | Jinja2 Templates · HTML/CSS/JS |
| Database | SQLite via SQLAlchemy |
| AI/LLM | Groq API · llama-3.1-8b-instant (free) |
| Styling | Custom dark theme CSS · DM Sans font |

---

## 📁 Project Structure

```
ai-ticketing/
├── backend/
│   ├── app/
│   │   ├── main.py              # All routes — UI pages + API endpoints
│   │   ├── models.py            # SQLAlchemy database models
│   │   ├── schemas.py           # Pydantic request/response schemas
│   │   ├── database.py          # SQLite connection and session
│   │   ├── config.py            # API keys and settings
│   │   ├── escalation.py        # Auto-escalation engine
│   │   ├── seed.py              # Sample departments and employees
│   │   └── routers/
│   │       ├── tickets.py       # Ticket API endpoints
│   │       ├── employees.py     # Employee API endpoints
│   │       └── analytics.py     # Analytics API endpoints
│   ├── ai_engine/
│   │   ├── analyzer.py          # Core AI analysis — calls Groq API
│   │   ├── resolver.py          # Auto-response generation
│   │   ├── router.py            # Department routing rules
│   │   └── similarity.py        # Similar ticket detection
│   ├── templates/
│   │   ├── base.html            # Base layout with sidebar
│   │   ├── dashboard.html       # Home dashboard
│   │   ├── submit.html          # Submit ticket form
│   │   ├── tickets.html         # Ticket list with filters
│   │   ├── ticket_detail.html   # Full ticket detail page
│   │   ├── employees.html       # Employee directory
│   │   ├── edit_employee.html   # Edit employee form
│   │   ├── analytics.html       # Analytics charts
│   │   ├── 404.html             # Not found page
│   │   └── 500.html             # Server error page
│   ├── static/
│   │   ├── css/style.css        # Complete dark theme styles
│   │   └── js/main.js           # Animations and keyboard shortcuts
│   └── requirements.txt
└── README.md
```

---

## ⚙️ Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/ai-ticketing.git
cd ai-ticketing
```

### 2. Create virtual environment

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Get your free Groq API key

1. Go to [console.groq.com](https://console.groq.com)
2. Sign up — completely free, no credit card
3. Click **API Keys** → **Create API Key**
4. Copy the key

### 5. Add your API key

Open `backend/app/config.py` and replace the placeholder:

```python
GROQ_API_KEY = "gsk_YOUR_KEY_HERE"
```

### 6. Seed the database

```bash
python -m app.seed
```

This creates 8 departments and 13 employees automatically.

### 7. Start the server

```bash
uvicorn app.main:app --reload --port 8000
```

### 8. Open in browser

```
http://localhost:8000
```

---

## 🗺️ All Pages

| URL | Page |
|-----|------|
| `http://localhost:8000/` | Dashboard |
| `http://localhost:8000/submit` | Submit new ticket |
| `http://localhost:8000/view/tickets` | All tickets with filters |
| `http://localhost:8000/view/tickets/{id}` | Ticket detail |
| `http://localhost:8000/employees` | Employee directory |
| `http://localhost:8000/analytics` | Analytics charts |
| `http://localhost:8000/docs` | Auto-generated API docs |

---

## 🤖 AI Modules

### Module 1 — AI Ticket Analysis
Every ticket is analyzed by Groq (llama-3.1-8b-instant) and returns:
```json
{
  "category": "DB | Bug | Access | HR | Server | Billing | Feature | Other",
  "summary": "2-3 sentence summary",
  "severity": "Critical | High | Medium | Low",
  "resolution_path": "Auto-resolve | Assign",
  "sentiment": "Frustrated | Neutral | Polite",
  "suggested_department": "Engineering | IT | HR | Finance | DevOps | Product | Legal",
  "confidence_score": 0-100,
  "estimated_resolution_time": "e.g. 2 hours"
}
```

### Module 2 — Auto-Resolution
If `resolution_path == "Auto-resolve"` the AI generates a professional human-like response and marks the ticket as Resolved instantly. Users can submit 👍/👎 feedback.

### Module 3 — Department Routing
Routing rules based on category + severity:
```
DB (any severity)        → Engineering
Server (Critical/High)   → DevOps
Bug (Critical/High)      → Engineering
Bug (Medium/Low)         → Product
Access (any)             → IT
Billing (any)            → Finance
HR (any)                 → HR
```

### Module 4 — Smart Assignment
Employees are scored for each ticket:
```
+40 per matching skill keyword
+30 if Available / +10 if Busy / +0 if On Leave
+30 minus (ticket load × 5)
```
Top 3 suggested assignees shown on ticket detail.

### Module 5 — Escalation Engine
Runs every 30 minutes. Finds Critical/High tickets unattended for 2+ hours and auto-reassigns to the next best available employee.

### Bonus — Similar Ticket Detection
Uses Jaccard keyword similarity to find related resolved tickets while the user is typing — before they even submit.

---

## ⌨️ Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `n` | Go to New Ticket |
| `t` | Go to Tickets list |
| `d` | Go to Dashboard |
| `Escape` | Close modal |
| `Ctrl+Enter` | Submit ticket form |

---

## 🧪 Test Scenarios

### Auto-resolve test
```
Title: "How many casual leaves do I have remaining?"
Body:  "I joined in January and want to know my leave balance."
Expected: Resolved instantly with AI response
```

### Assignment test
```
Title: "Login button not working on mobile app"
Body:  "Android login button unresponsive. Demo in 2 hours."
Expected: High severity, Bug category, routed to Engineering
```

### Critical routing test
```
Title: "Production database completely down"
Body:  "PostgreSQL stopped. All 500 users affected."
Expected: Critical severity, DB category, routed to Engineering
```

### Low confidence test
```
Title: "help"
Body:  "fix please"
Expected: 0% confidence, amber warning, force-assigned to human
```

---

## 📊 Database Schema

| Table | Purpose |
|-------|---------|
| `tickets` | All submitted tickets |
| `ai_analysis` | AI output for each ticket |
| `employees` | Employee directory |
| `departments` | Department list |
| `ticket_logs` | Full audit trail |
| `feedback` | 👍/👎 on auto-resolved tickets |

---

## 🔧 Configuration

All settings in `backend/app/config.py`:

```python
GROQ_API_KEY = "your-key-here"
DATABASE_URL = "sqlite:///./ticketing.db"
AI_MODEL = "llama-3.1-8b-instant"
AI_RETRY_ATTEMPTS = 3
CONFIDENCE_THRESHOLD = 60    # Below this → force human assignment
ESCALATION_HOURS = 2         # Hours before auto-escalation
```

---

## 📦 Dependencies

```
fastapi==0.111.0
uvicorn==0.29.0
sqlalchemy==2.0.30
groq==0.9.0
pydantic==2.7.1
python-multipart==0.0.9
httpx==0.27.0
jinja2
aiofiles
```

---

## 👨‍💻 Built With

- **FastAPI** — Modern Python web framework
- **Groq API** — Free LLM inference (llama-3.1-8b-instant)
- **SQLAlchemy** — Python ORM for SQLite
- **Jinja2** — Server-side HTML templating
- **DM Sans** — Clean sans-serif font

---

## 📄 License

MIT License — free to use, modify and distribute.
