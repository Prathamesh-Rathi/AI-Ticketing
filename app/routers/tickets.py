# backend/app/routers/tickets.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime
from typing import List, Optional

from app.database import get_db
from app import models
from app.schemas import TicketCreate, TicketOut, TicketStatusUpdate, TicketAssign, FeedbackCreate
from ai_engine.analyzer import analyze_ticket
from ai_engine.resolver import generate_auto_response
from ai_engine.router import get_department_for_ticket, get_routing_explanation

router = APIRouter(prefix="/tickets", tags=["Tickets"])


# ─────────────────────────────────────────────
# Helper — add log entry
# ─────────────────────────────────────────────

def add_log(db: Session, ticket_id: int, actor: str, action: str, note: str = None):
    log = models.TicketLog(
        ticket_id=ticket_id,
        actor=actor,
        action=action,
        note=note
    )
    db.add(log)
    db.commit()


# ─────────────────────────────────────────────
# POST /tickets — Submit a new ticket
# ─────────────────────────────────────────────

@router.post("/", response_model=TicketOut)
def submit_ticket(payload: TicketCreate, db: Session = Depends(get_db)):

    # Step 1 — Create ticket in DB
    ticket = models.Ticket(
        title=payload.title,
        body=payload.body,
        submitter_name=payload.submitter_name,
        submitter_email=payload.submitter_email,
        status="New"
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    add_log(db, ticket.id, payload.submitter_name, "Ticket submitted")

    # Step 2 — Run AI analysis
    ai_result = analyze_ticket(payload.title, payload.body)

    # Step 3 — Determine department from routing rules
    department_name = get_department_for_ticket(
        ai_result["category"],
        ai_result["severity"],
        ai_result.get("suggested_department", "")
    )

    # Find department in DB
    department = db.query(models.Department).filter(
        models.Department.name == department_name
    ).first()

    # Step 4 — Handle auto-resolve vs assign
    auto_response = None

    if ai_result["resolution_path"] == "Auto-resolve":
        # Generate contextual AI response
        auto_response = generate_auto_response(
            title=payload.title,
            body=payload.body,
            category=ai_result["category"],
            summary=ai_result["summary"],
            submitter_name=payload.submitter_name
        )
        ticket.status = "Resolved"
        ticket.resolved_at = datetime.utcnow()
        add_log(db, ticket.id, "AI System", "Auto-resolved by AI", auto_response[:200])

    else:
        ticket.status = "Assigned" if department else "New"
        if department:
            ticket.department_id = department.id
            add_log(db, ticket.id, "AI System", f"Routed to {department_name} department")

    # Step 5 — Save AI analysis
    analysis = models.AIAnalysis(
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
            ai_result["category"],
            ai_result["severity"],
            department_name
        )
    )
    db.add(analysis)
    db.commit()
    db.refresh(ticket)

    return ticket


# ─────────────────────────────────────────────
# GET /tickets — List all tickets with filters
# ─────────────────────────────────────────────

@router.get("/", response_model=List[TicketOut])
def list_tickets(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    department_id: Optional[int] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.Ticket)

    if status:
        query = query.filter(models.Ticket.status == status)
    if department_id:
        query = query.filter(models.Ticket.department_id == department_id)
    if severity:
        query = query.join(models.AIAnalysis).filter(
            models.AIAnalysis.severity == severity
        )
    if category:
        query = query.join(models.AIAnalysis).filter(
            models.AIAnalysis.category == category
        )

    return query.order_by(desc(models.Ticket.created_at)).all()


# ─────────────────────────────────────────────
# GET /tickets/{id} — Get single ticket
# ─────────────────────────────────────────────

@router.get("/{ticket_id}", response_model=TicketOut)
def get_ticket(ticket_id: int, db: Session = Depends(get_db)):
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


# ─────────────────────────────────────────────
# PATCH /tickets/{id}/status — Update status
# ─────────────────────────────────────────────

@router.patch("/{ticket_id}/status")
def update_status(ticket_id: int, payload: TicketStatusUpdate, db: Session = Depends(get_db)):
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    old_status = ticket.status
    ticket.status = payload.status

    if payload.status == "Resolved":
        ticket.resolved_at = datetime.utcnow()

    db.commit()

    add_log(
        db, ticket_id,
        payload.actor,
        f"Status changed from {old_status} to {payload.status}",
        payload.note
    )

    return {"message": "Status updated", "ticket_id": ticket_id, "status": payload.status}


# ─────────────────────────────────────────────
# PATCH /tickets/{id}/assign — Assign to employee
# ─────────────────────────────────────────────

@router.patch("/{ticket_id}/assign")
def assign_ticket(ticket_id: int, payload: TicketAssign, db: Session = Depends(get_db)):
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    employee = db.query(models.Employee).filter(models.Employee.id == payload.employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Update old assignee load
    if ticket.assignee_id:
        old_emp = db.query(models.Employee).filter(
            models.Employee.id == ticket.assignee_id
        ).first()
        if old_emp and old_emp.current_ticket_load > 0:
            old_emp.current_ticket_load -= 1

    # Assign new employee
    ticket.assignee_id = payload.employee_id
    ticket.status = "Assigned"
    employee.current_ticket_load += 1

    db.commit()

    add_log(
        db, ticket_id,
        payload.actor,
        f"Ticket assigned to {employee.name}"
    )

    return {
        "message": "Ticket assigned",
        "ticket_id": ticket_id,
        "assigned_to": employee.name
    }


# ─────────────────────────────────────────────
# POST /tickets/{id}/feedback — Submit feedback
# ─────────────────────────────────────────────

@router.post("/{ticket_id}/feedback")
def submit_feedback(ticket_id: int, payload: FeedbackCreate, db: Session = Depends(get_db)):
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    existing = db.query(models.Feedback).filter(
        models.Feedback.ticket_id == ticket_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Feedback already submitted")

    feedback = models.Feedback(
        ticket_id=ticket_id,
        helpful=payload.helpful,
        comment=payload.comment
    )
    db.add(feedback)
    db.commit()

    add_log(
        db, ticket_id,
        "User",
        f"Feedback submitted: {'Helpful' if payload.helpful else 'Not helpful'}"
    )

    return {"message": "Feedback recorded", "helpful": payload.helpful}


# ─────────────────────────────────────────────
# GET /tickets/{id}/suggest-assignees
# Smart employee suggestion based on skills + load
# ─────────────────────────────────────────────

@router.get("/{ticket_id}/suggest-assignees")
def suggest_assignees(ticket_id: int, db: Session = Depends(get_db)):
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if not ticket.ai_analysis:
        raise HTTPException(status_code=400, detail="No AI analysis found for this ticket")

    category = ticket.ai_analysis.category
    department_name = ticket.ai_analysis.suggested_department

    # Skill map — category → relevant skill keywords
    SKILL_MAP = {
        "DB":      ["Database", "SQL", "PostgreSQL", "MongoDB"],
        "Server":  ["Server", "Linux", "DevOps", "Infrastructure"],
        "Bug":     ["Python", "JavaScript", "Backend", "Frontend", "Engineering"],
        "Access":  ["Networking", "Active Directory", "IT Support"],
        "Billing": ["Payroll", "Finance", "Accounting"],
        "HR":      ["HR", "Recruitment", "Policy"],
        "Feature": ["Product", "Design", "Frontend"],
        "Other":   ["IT Support", "General"],
    }

    relevant_skills = SKILL_MAP.get(category, ["IT Support"])

    # Get employees from the right department who are active
    dept = db.query(models.Department).filter(
        models.Department.name == department_name
    ).first()

    employees_query = db.query(models.Employee).filter(
        models.Employee.is_active == True
    )
    if dept:
        employees_query = employees_query.filter(
            models.Employee.department_id == dept.id
        )

    employees = employees_query.all()

    # Score each employee
    scored = []
    for emp in employees:
        score = 0
        emp_skills = [s.strip().lower() for s in emp.skill_tags.split(",")]

        # Skill match — highest priority
        for skill in relevant_skills:
            if skill.lower() in emp_skills:
                score += 40

        # Availability score
        availability_score = {"Available": 30, "Busy": 10, "On Leave": 0}
        score += availability_score.get(emp.availability, 0)

        # Load score — lower load = higher score
        load_score = max(0, 30 - (emp.current_ticket_load * 5))
        score += load_score

        scored.append({
            "id": emp.id,
            "name": emp.name,
            "email": emp.email,
            "role": emp.role,
            "availability": emp.availability,
            "current_ticket_load": emp.current_ticket_load,
            "skill_tags": emp.skill_tags,
            "score": score
        })

    # Sort by score descending, return top 3
    scored.sort(key=lambda x: x["score"], reverse=True)
    return {"suggested_assignees": scored[:3]}