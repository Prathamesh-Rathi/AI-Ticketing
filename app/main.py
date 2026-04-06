# backend/app/main.py

from fastapi import FastAPI, Request, Form, Depends, Body
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from datetime import datetime
from typing import Optional
import asyncio

from app.config import APP_NAME, APP_VERSION
from app.database import engine, Base, get_db
from app import models
from app.routers import tickets as ticket_router
from app.routers import employees as employee_router
from app.routers import analytics as analytics_router
from ai_engine.analyzer import analyze_ticket
from ai_engine.resolver import generate_auto_response
from ai_engine.router import get_department_for_ticket, get_routing_explanation
from ai_engine.similarity import find_similar_tickets

app = FastAPI(title=APP_NAME, version=APP_VERSION)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routers — all prefixed with /api to avoid clashing with UI pages
app.include_router(ticket_router.router)
app.include_router(employee_router.router)
app.include_router(analytics_router.router)


# ─────────────────────────────────────────────
# STARTUP
# ─────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables ready")
    asyncio.create_task(escalation_loop())


# ─────────────────────────────────────────────
# BACKGROUND ESCALATION LOOP
# ─────────────────────────────────────────────

async def escalation_loop():
    while True:
        await asyncio.sleep(1800)
        try:
            from app.escalation import run_escalation
            run_escalation()
            print("✅ Escalation check completed")
        except Exception as e:
            print(f"❌ Escalation error: {e}")


# ─────────────────────────────────────────────
# ERROR HANDLERS
# ─────────────────────────────────────────────

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return templates.TemplateResponse(
        "404.html",
        {"request": request, "active": ""},
        status_code=404
    )

@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    return templates.TemplateResponse(
        "500.html",
        {"request": request, "active": "", "error": str(exc)},
        status_code=500
    )


# ─────────────────────────────────────────────
# HELPER
# ─────────────────────────────────────────────

def add_log(db, ticket_id, actor, action, note=None):
    db.add(models.TicketLog(
        ticket_id=ticket_id,
        actor=actor,
        action=action,
        note=note
    ))
    db.commit()


# ─────────────────────────────────────────────
# PAGE: Dashboard
# ─────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    total         = db.query(models.Ticket).count()
    open_tickets  = db.query(models.Ticket).filter(
        models.Ticket.status.in_(["New","Assigned","In Progress","Pending Info"])
    ).count()
    resolved      = db.query(models.Ticket).filter(
        models.Ticket.status == "Resolved"
    ).count()
    closed        = db.query(models.Ticket).filter(
        models.Ticket.status == "Closed"
    ).count()
    auto_resolved = db.query(models.AIAnalysis).filter_by(
        resolution_path="Auto-resolve"
    ).count()
    helpful       = db.query(models.Feedback).filter_by(helpful=True).count()
    total_fb      = db.query(models.Feedback).count()
    success_rate  = f"{round(helpful/total_fb*100,1)}%" if total_fb > 0 else "0%"

    recent_tickets = db.query(models.Ticket)\
        .order_by(desc(models.Ticket.created_at)).limit(8).all()

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "active": "dashboard",
        "summary": {
            "total_tickets":                total,
            "open_tickets":                 open_tickets,
            "resolved_tickets":             resolved,
            "closed_tickets":               closed,
            "auto_resolved":                auto_resolved,
            "auto_resolution_success_rate": success_rate,
        },
        "recent_tickets": recent_tickets,
    })


# ─────────────────────────────────────────────
# PAGE: Submit ticket GET
# ─────────────────────────────────────────────

@app.get("/submit", response_class=HTMLResponse)
def submit_page(request: Request):
    return templates.TemplateResponse("submit.html", {
        "request": request, "active": "submit"
    })


# ─────────────────────────────────────────────
# PAGE: Submit ticket POST
# ─────────────────────────────────────────────

@app.post("/submit")
def submit_ticket(
    request: Request,
    title: str = Form(...),
    body: str = Form(...),
    submitter_name: str = Form(...),
    submitter_email: str = Form(...),
    db: Session = Depends(get_db)
):
    # Save ticket
    ticket = models.Ticket(
        title=title, body=body,
        submitter_name=submitter_name,
        submitter_email=submitter_email,
        status="New"
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    add_log(db, ticket.id, submitter_name, "Ticket submitted")

    # AI analysis
    ai_result = analyze_ticket(title, body)
    dept_name = get_department_for_ticket(
        ai_result["category"],
        ai_result["severity"],
        ai_result.get("suggested_department", "")
    )
    department    = db.query(models.Department).filter_by(name=dept_name).first()
    auto_response = None

    if ai_result["resolution_path"] == "Auto-resolve":
        auto_response = generate_auto_response(
            title, body,
            ai_result["category"],
            ai_result["summary"],
            submitter_name
        )
        ticket.status      = "Resolved"
        ticket.resolved_at = datetime.utcnow()
        add_log(db, ticket.id, "AI System",
                "Auto-resolved by AI", auto_response[:200])
    else:
        ticket.status = "Assigned" if department else "New"
        if department:
            ticket.department_id = department.id
            add_log(db, ticket.id, "AI System",
                    f"Routed to {dept_name} department")

    db.add(models.AIAnalysis(
        ticket_id=ticket.id,
        category=ai_result["category"],
        summary=ai_result["summary"],
        severity=ai_result["severity"],
        resolution_path=ai_result["resolution_path"],
        sentiment=ai_result["sentiment"],
        suggested_department=ai_result.get("suggested_department", ""),
        suggested_employee=ai_result.get("suggested_employee", ""),
        confidence_score=ai_result["confidence_score"],
        estimated_resolution_time=ai_result.get("estimated_resolution_time", ""),
        auto_response=auto_response,
        routing_reason=get_routing_explanation(
            ai_result["category"], ai_result["severity"], dept_name
        )
    ))
    db.commit()

    # Redirect to the UI page — NOT the API endpoint
    return RedirectResponse(
        f"/view/tickets/{ticket.id}?flash=Ticket analyzed and routed by AI",
        status_code=303
    )


# ─────────────────────────────────────────────
# PAGE: Ticket list
# ─────────────────────────────────────────────

@app.get("/view/tickets", response_class=HTMLResponse)
def tickets_page(
    request: Request,
    search: str = "",
    status: str = "",
    severity: str = "",
    category: str = "",
    db: Session = Depends(get_db)
):
    query = db.query(models.Ticket)
    if status:
        query = query.filter(models.Ticket.status == status)
    if severity:
        query = query.join(models.AIAnalysis).filter(
            models.AIAnalysis.severity == severity
        )
    if category:
        query = query.join(models.AIAnalysis).filter(
            models.AIAnalysis.category == category
        )

    all_tickets = query.order_by(desc(models.Ticket.created_at)).all()

    if search:
        s = search.lower()
        all_tickets = [
            t for t in all_tickets
            if s in t.title.lower() or s in t.submitter_name.lower()
        ]

    return templates.TemplateResponse("tickets.html", {
        "request":         request,
        "active":          "tickets",
        "tickets":         all_tickets,
        "search":          search,
        "status_filter":   status,
        "severity_filter": severity,
        "category_filter": category,
    })


# ─────────────────────────────────────────────
# PAGE: Ticket detail
# ─────────────────────────────────────────────

@app.get("/view/tickets/{ticket_id}", response_class=HTMLResponse)
def ticket_detail_page(
    ticket_id: int,
    request: Request,
    flash: str = "",
    db: Session = Depends(get_db)
):
    ticket = db.query(models.Ticket).filter_by(id=ticket_id).first()
    if not ticket:
        return templates.TemplateResponse(
            "404.html",
            {"request": request, "active": "tickets"},
            status_code=404
        )

    # Smart assignee suggestions
    suggestions = []
    if ticket.ai_analysis:
        SKILL_MAP = {
            "DB":      ["database","sql","postgresql","mongodb"],
            "Server":  ["server","linux","devops","infrastructure"],
            "Bug":     ["python","javascript","backend","frontend"],
            "Access":  ["networking","active directory","it support"],
            "Billing": ["payroll","finance","accounting"],
            "HR":      ["hr","recruitment","policy"],
            "Feature": ["product","design","frontend"],
            "Other":   ["it support","general"],
        }
        relevant  = SKILL_MAP.get(ticket.ai_analysis.category, ["it support"])
        dept      = db.query(models.Department).filter_by(
            name=ticket.ai_analysis.suggested_department
        ).first()
        emp_query = db.query(models.Employee).filter_by(is_active=True)
        if dept:
            emp_query = emp_query.filter_by(department_id=dept.id)

        for emp in emp_query.all():
            score      = 0
            emp_skills = [s.strip().lower() for s in emp.skill_tags.split(",")]
            for skill in relevant:
                if skill in emp_skills:
                    score += 40
            score += {"Available":30,"Busy":10,"On Leave":0}.get(
                emp.availability, 0
            )
            score += max(0, 30 - emp.current_ticket_load * 5)
            suggestions.append({
                "id":                  emp.id,
                "name":                emp.name,
                "role":                emp.role,
                "availability":        emp.availability,
                "current_ticket_load": emp.current_ticket_load,
                "score":               score
            })
        suggestions = sorted(
            suggestions, key=lambda x: x["score"], reverse=True
        )[:3]

    # Similar tickets
    similar = []
    if ticket.ai_analysis:
        similar = find_similar_tickets(
            title=ticket.title,
            body=ticket.body,
            category=ticket.ai_analysis.category,
            db=db,
            exclude_ticket_id=ticket.id,
            limit=3
        )

    return templates.TemplateResponse("ticket_detail.html", {
        "request":       request,
        "active":        "tickets",
        "ticket":        ticket,
        "suggestions":   suggestions,
        "similar":       similar,
        "flash_success": flash,
    })


# PAGE: Update status POST
@app.post("/view/tickets/{ticket_id}/status")
def update_ticket_status(
    ticket_id: int,
    status: str = Form(...),
    note: str = Form(""),
    actor: str = Form("Agent"),
    db: Session = Depends(get_db)
):
    ticket = db.query(models.Ticket).filter_by(id=ticket_id).first()
    if ticket:
        old = ticket.status
        ticket.status = status
        if status == "Resolved":
            ticket.resolved_at = datetime.utcnow()
        db.commit()
        add_log(
            db, ticket_id, actor,
            f"Status changed from {old} to {status}",
            note or None
        )
    return RedirectResponse(
        f"/view/tickets/{ticket_id}?flash=Status updated to {status}",
        status_code=303
    )


# PAGE: Assign ticket POST
@app.post("/view/tickets/{ticket_id}/assign")
def assign_ticket_page(
    ticket_id: int,
    employee_id: int = Form(...),
    actor: str = Form("Admin"),
    db: Session = Depends(get_db)
):
    ticket = db.query(models.Ticket).filter_by(id=ticket_id).first()
    emp    = db.query(models.Employee).filter_by(id=employee_id).first()
    if ticket and emp:
        if ticket.assignee_id:
            old_emp = db.query(models.Employee).filter_by(
                id=ticket.assignee_id
            ).first()
            if old_emp and old_emp.current_ticket_load > 0:
                old_emp.current_ticket_load -= 1
        ticket.assignee_id = employee_id
        ticket.status      = "Assigned"
        emp.current_ticket_load += 1
        db.commit()
        add_log(db, ticket_id, actor, f"Ticket assigned to {emp.name}")
    return RedirectResponse(
        f"/view/tickets/{ticket_id}?flash=Assigned to {emp.name if emp else 'agent'}",
        status_code=303
    )


# PAGE: Feedback POST
@app.post("/view/tickets/{ticket_id}/feedback")
def submit_feedback_page(
    ticket_id: int,
    helpful: str = Form(...),
    db: Session = Depends(get_db)
):
    existing = db.query(models.Feedback).filter_by(ticket_id=ticket_id).first()
    if not existing:
        db.add(models.Feedback(
            ticket_id=ticket_id,
            helpful=(helpful == "true")
        ))
        db.commit()
        add_log(
            db, ticket_id, "User",
            f"Feedback: {'Helpful' if helpful=='true' else 'Not helpful'}"
        )
    return RedirectResponse(
        f"/view/tickets/{ticket_id}?flash=Feedback recorded, thank you!",
        status_code=303
    )


# ─────────────────────────────────────────────
# PAGE: Employees
# ─────────────────────────────────────────────

@app.get("/employees", response_class=HTMLResponse)
def employees_page(
    request: Request,
    flash: str = "",
    db: Session = Depends(get_db)
):
    employees   = db.query(models.Employee).filter_by(is_active=True).all()
    departments = db.query(models.Department).all()
    dept_map    = {d.id: d.name for d in departments}
    return templates.TemplateResponse("employees.html", {
        "request":       request,
        "active":        "employees",
        "employees":     employees,
        "departments":   departments,
        "dept_map":      dept_map,
        "flash_success": flash,
    })


@app.post("/employees")
def add_employee(
    name: str = Form(...),
    email: str = Form(...),
    role: str = Form(...),
    department_id: int = Form(...),
    skill_tags: str = Form(""),
    availability: str = Form("Available"),
    db: Session = Depends(get_db)
):
    existing = db.query(models.Employee).filter_by(email=email).first()
    if not existing:
        db.add(models.Employee(
            name=name, email=email, role=role,
            department_id=department_id,
            skill_tags=skill_tags,
            availability=availability
        ))
        db.commit()
    return RedirectResponse(
        "/employees?flash=Team member added successfully",
        status_code=303
    )


@app.get("/employees/{emp_id}/edit", response_class=HTMLResponse)
def edit_employee_page(
    emp_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    emp = db.query(models.Employee).filter_by(id=emp_id).first()
    if not emp:
        return templates.TemplateResponse(
            "404.html",
            {"request": request, "active": "employees"},
            status_code=404
        )
    departments = db.query(models.Department).all()
    return templates.TemplateResponse("edit_employee.html", {
        "request":     request,
        "active":      "employees",
        "emp":         emp,
        "departments": departments,
    })


@app.post("/employees/{emp_id}/edit")
def edit_employee(
    emp_id: int,
    name: str = Form(...),
    role: str = Form(...),
    department_id: int = Form(...),
    skill_tags: str = Form(""),
    availability: str = Form("Available"),
    db: Session = Depends(get_db)
):
    emp = db.query(models.Employee).filter_by(id=emp_id).first()
    if emp:
        emp.name          = name
        emp.role          = role
        emp.department_id = department_id
        emp.skill_tags    = skill_tags
        emp.availability  = availability
        db.commit()
    return RedirectResponse(
        f"/employees?flash={name} updated successfully",
        status_code=303
    )


@app.post("/employees/{emp_id}/deactivate")
def deactivate_emp_page(emp_id: int, db: Session = Depends(get_db)):
    emp = db.query(models.Employee).filter_by(id=emp_id).first()
    if emp:
        emp.is_active = False
        db.commit()
    return RedirectResponse(
        "/employees?flash=Team member removed",
        status_code=303
    )


# ─────────────────────────────────────────────
# PAGE: Analytics
# ─────────────────────────────────────────────

@app.get("/analytics", response_class=HTMLResponse)
def analytics_page(request: Request, db: Session = Depends(get_db)):
    total         = db.query(models.Ticket).count()
    open_tickets  = db.query(models.Ticket).filter(
        models.Ticket.status.in_(["New","Assigned","In Progress","Pending Info"])
    ).count()
    auto_resolved = db.query(models.AIAnalysis).filter_by(
        resolution_path="Auto-resolve"
    ).count()
    helpful      = db.query(models.Feedback).filter_by(helpful=True).count()
    total_fb     = db.query(models.Feedback).count()
    success_rate = f"{round(helpful/total_fb*100,1)}%" if total_fb > 0 else "0%"

    dept_data = [
        {"department": r[0], "ticket_count": r[1]} for r in
        db.query(models.Department.name, func.count(models.Ticket.id))
          .join(models.Ticket, models.Ticket.department_id == models.Department.id)
          .group_by(models.Department.name).all()
    ]
    cat_data = [
        {"category": r[0], "count": r[1]} for r in
        db.query(models.AIAnalysis.category, func.count(models.AIAnalysis.id))
          .group_by(models.AIAnalysis.category)
          .order_by(func.count(models.AIAnalysis.id).desc()).limit(5).all()
    ]
    sev_data = [
        {"severity": r[0], "count": r[1]} for r in
        db.query(models.AIAnalysis.severity, func.count(models.AIAnalysis.id))
          .group_by(models.AIAnalysis.severity).all()
    ]
    status_data = [
        {"status": r[0], "count": r[1]} for r in
        db.query(models.Ticket.status, func.count(models.Ticket.id))
          .group_by(models.Ticket.status).all()
    ]

    return templates.TemplateResponse("analytics.html", {
        "request": request,
        "active":  "analytics",
        "summary": {
            "total_tickets":                total,
            "open_tickets":                 open_tickets,
            "auto_resolved":                auto_resolved,
            "auto_resolution_success_rate": success_rate,
        },
        "dept_data":   dept_data,
        "cat_data":    cat_data,
        "sev_data":    sev_data,
        "status_data": status_data,
    })


# ─────────────────────────────────────────────
# API: Similar ticket search
# ─────────────────────────────────────────────

@app.post("/api/similar-search")
def similar_search(
    data: dict = Body(...),
    db: Session = Depends(get_db)
):
    title = data.get("title", "")
    body  = data.get("body",  "")
    text  = f"{title} {body}".lower()

    if any(w in text for w in ["database","db","sql","postgres","mongo"]):
        category = "DB"
    elif any(w in text for w in ["server","down","crash","infrastructure","deploy"]):
        category = "Server"
    elif any(w in text for w in ["bug","error","broken","crash","exception","fail"]):
        category = "Bug"
    elif any(w in text for w in ["access","login","password","permission","account"]):
        category = "Access"
    elif any(w in text for w in ["billing","invoice","payment","charge","refund"]):
        category = "Billing"
    elif any(w in text for w in ["hr","leave","policy","salary","payroll","holiday"]):
        category = "HR"
    elif any(w in text for w in ["feature","request","add","improve","suggestion"]):
        category = "Feature"
    else:
        category = "Other"

    similar = find_similar_tickets(
        title=title, body=body,
        category=category, db=db, limit=3
    )
    return {"similar": similar, "category_guess": category}


# ─────────────────────────────────────────────
# API: Manual escalation trigger
# ─────────────────────────────────────────────

@app.post("/api/run-escalation")
def trigger_escalation():
    from app.escalation import run_escalation
    run_escalation()
    return {"message": "Escalation check completed"}