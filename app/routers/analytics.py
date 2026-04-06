# backend/app/routers/analytics.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app import models

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("/summary")
def get_summary(db: Session = Depends(get_db)):
    total = db.query(models.Ticket).count()
    open_tickets = db.query(models.Ticket).filter(
        models.Ticket.status.in_(["New", "Assigned", "In Progress", "Pending Info"])
    ).count()
    resolved = db.query(models.Ticket).filter(
        models.Ticket.status == "Resolved"
    ).count()
    closed = db.query(models.Ticket).filter(
        models.Ticket.status == "Closed"
    ).count()
    auto_resolved = db.query(models.AIAnalysis).filter(
        models.AIAnalysis.resolution_path == "Auto-resolve"
    ).count()

    # Auto resolution success rate
    helpful = db.query(models.Feedback).filter(
        models.Feedback.helpful == True
    ).count()
    total_feedback = db.query(models.Feedback).count()
    success_rate = round((helpful / total_feedback * 100), 1) if total_feedback > 0 else 0

    return {
        "total_tickets": total,
        "open_tickets": open_tickets,
        "resolved_tickets": resolved,
        "closed_tickets": closed,
        "auto_resolved": auto_resolved,
        "auto_resolution_success_rate": f"{success_rate}%",
        "total_feedback": total_feedback
    }


@router.get("/by-department")
def tickets_by_department(db: Session = Depends(get_db)):
    results = db.query(
        models.Department.name,
        func.count(models.Ticket.id).label("ticket_count")
    ).join(
        models.Ticket,
        models.Ticket.department_id == models.Department.id
    ).group_by(models.Department.name).all()

    return [{"department": r[0], "ticket_count": r[1]} for r in results]


@router.get("/by-category")
def tickets_by_category(db: Session = Depends(get_db)):
    results = db.query(
        models.AIAnalysis.category,
        func.count(models.AIAnalysis.id).label("count")
    ).group_by(models.AIAnalysis.category)\
     .order_by(func.count(models.AIAnalysis.id).desc())\
     .limit(5).all()

    return [{"category": r[0], "count": r[1]} for r in results]


@router.get("/by-severity")
def tickets_by_severity(db: Session = Depends(get_db)):
    results = db.query(
        models.AIAnalysis.severity,
        func.count(models.AIAnalysis.id).label("count")
    ).group_by(models.AIAnalysis.severity).all()

    return [{"severity": r[0], "count": r[1]} for r in results]


@router.get("/by-status")
def tickets_by_status(db: Session = Depends(get_db)):
    results = db.query(
        models.Ticket.status,
        func.count(models.Ticket.id).label("count")
    ).group_by(models.Ticket.status).all()

    return [{"status": r[0], "count": r[1]} for r in results]