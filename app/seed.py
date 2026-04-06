# backend/app/seed.py
# Run this ONCE to populate departments and employees

from app.database import SessionLocal, engine, Base
from app import models

Base.metadata.create_all(bind=engine)
db = SessionLocal()

# ── Departments ──────────────────────────────
departments = [
    {"name": "Engineering",  "description": "Backend, frontend, and infrastructure engineering"},
    {"name": "DevOps",       "description": "Servers, deployments, CI/CD pipelines"},
    {"name": "IT",           "description": "Internal IT support, access, networking"},
    {"name": "HR",           "description": "Human resources, policies, recruitment"},
    {"name": "Finance",      "description": "Billing, payroll, accounts"},
    {"name": "Product",      "description": "Product management and design"},
    {"name": "Legal",        "description": "Legal and compliance"},
    {"name": "Management",   "description": "Leadership and executive team"},
]

dept_map = {}
for d in departments:
    existing = db.query(models.Department).filter_by(name=d["name"]).first()
    if not existing:
        obj = models.Department(**d)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        dept_map[d["name"]] = obj.id
    else:
        dept_map[d["name"]] = existing.id

print("✅ Departments seeded")

# ── Employees ────────────────────────────────
employees = [
    # Engineering
    {"name": "Riya Sharma",    "email": "riya@company.com",    "role": "Senior Backend Engineer", "department_id": dept_map["Engineering"], "skill_tags": "Python,Database,SQL,Backend",          "availability": "Available"},
    {"name": "Arjun Mehta",    "email": "arjun@company.com",   "role": "Full Stack Engineer",     "department_id": dept_map["Engineering"], "skill_tags": "JavaScript,React,Backend,Frontend",    "availability": "Busy"},
    {"name": "Sneha Patil",    "email": "sneha@company.com",   "role": "Database Engineer",       "department_id": dept_map["Engineering"], "skill_tags": "Database,SQL,MongoDB,PostgreSQL",      "availability": "Available"},

    # DevOps
    {"name": "Karan Joshi",    "email": "karan@company.com",   "role": "DevOps Engineer",         "department_id": dept_map["DevOps"],      "skill_tags": "Server,Linux,Docker,Infrastructure",  "availability": "Available"},
    {"name": "Priya Nair",     "email": "priya@company.com",   "role": "Site Reliability Eng",   "department_id": dept_map["DevOps"],      "skill_tags": "Server,Kubernetes,Linux,Monitoring",  "availability": "On Leave"},

    # IT
    {"name": "Amit Desai",     "email": "amit@company.com",    "role": "IT Support Lead",         "department_id": dept_map["IT"],          "skill_tags": "Networking,Active Directory,IT Support","availability": "Available"},
    {"name": "Neha Kulkarni",  "email": "neha@company.com",    "role": "IT Support Engineer",     "department_id": dept_map["IT"],          "skill_tags": "IT Support,Networking,Hardware",      "availability": "Available"},

    # HR
    {"name": "Pooja Iyer",     "email": "pooja@company.com",   "role": "HR Manager",              "department_id": dept_map["HR"],          "skill_tags": "HR,Policy,Recruitment",               "availability": "Available"},
    {"name": "Rahul Gupta",    "email": "rahul@company.com",   "role": "HR Executive",            "department_id": dept_map["HR"],          "skill_tags": "HR,Payroll,Policy",                   "availability": "Busy"},

    # Finance
    {"name": "Sunita Rao",     "email": "sunita@company.com",  "role": "Finance Manager",         "department_id": dept_map["Finance"],     "skill_tags": "Payroll,Finance,Accounting",          "availability": "Available"},
    {"name": "Vikram Shah",    "email": "vikram@company.com",  "role": "Billing Specialist",      "department_id": dept_map["Finance"],     "skill_tags": "Billing,Finance,Accounting",          "availability": "Available"},

    # Product
    {"name": "Divya Menon",    "email": "divya@company.com",   "role": "Product Manager",         "department_id": dept_map["Product"],     "skill_tags": "Product,Design,Frontend",             "availability": "Available"},

    # Legal
    {"name": "Rohan Verma",    "email": "rohan@company.com",   "role": "Legal Counsel",           "department_id": dept_map["Legal"],       "skill_tags": "Legal,Compliance,Contracts",          "availability": "Available"},
]

for e in employees:
    existing = db.query(models.Employee).filter_by(email=e["email"]).first()
    if not existing:
        obj = models.Employee(**e)
        db.add(obj)
        db.commit()

print("✅ Employees seeded")
print("✅ Seed complete — ready to go!")
db.close()