# backend/app/escalation.py
# Run this as a background job — checks every 30 mins for unattended tickets

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app import models

def run_escalation():
    """
    Finds Critical/High tickets that have been in 'New' or 'Assigned'
    status for more than 2 hours without being picked up,
    and reassigns them to the next best available employee.
    """
    db: Session = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(hours=0)

        # Find stale high-priority tickets
        stale_tickets = db.query(models.Ticket).join(models.AIAnalysis).filter(
            models.Ticket.status.in_(["New", "Assigned"]),
            models.AIAnalysis.severity.in_(["Critical", "High"]),
            models.Ticket.created_at <= cutoff
        ).all()

        if not stale_tickets:
            print("✅ Escalation check: no stale tickets found")
            return

        for ticket in stale_tickets:
            print(f"⚠️  Escalating ticket #{ticket.id}: {ticket.title}")

            ai = ticket.ai_analysis
            if not ai:
                continue

            # Find the best available employee in the suggested department
            dept = db.query(models.Department).filter_by(
                name=ai.suggested_department
            ).first()

            emp_query = db.query(models.Employee).filter(
                models.Employee.is_active == True,
                models.Employee.availability == "Available"
            )
            if dept:
                emp_query = emp_query.filter(
                    models.Employee.department_id == dept.id
                )

            # Skip current assignee if already assigned
            if ticket.assignee_id:
                emp_query = emp_query.filter(
                    models.Employee.id != ticket.assignee_id
                )

            # Pick employee with lowest load
            employees = emp_query.order_by(
                models.Employee.current_ticket_load.asc()
            ).all()

            if not employees:
                # Log escalation even if no one available
                db.add(models.TicketLog(
                    ticket_id=ticket.id,
                    actor="Escalation System",
                    action=f"Escalation triggered — no available agent found in {ai.suggested_department}",
                    note="Manual intervention required"
                ))
                db.commit()
                continue

            new_assignee = employees[0]

            # Release old assignee load
            if ticket.assignee_id:
                old = db.query(models.Employee).filter_by(
                    id=ticket.assignee_id
                ).first()
                if old and old.current_ticket_load > 0:
                    old.current_ticket_load -= 1

            # Reassign
            ticket.assignee_id = new_assignee.id
            ticket.status = "Assigned"
            new_assignee.current_ticket_load += 1

            db.add(models.TicketLog(
                ticket_id=ticket.id,
                actor="Escalation System",
                action=f"🚨 Auto-escalated to {new_assignee.name}",
                note=f"Ticket was unattended for 2+ hours. Severity: {ai.severity}. Auto-reassigned to next available agent."
            ))
            db.commit()
            print(f"   → Reassigned to {new_assignee.name}")

    finally:
        db.close()


if __name__ == "__main__":
    print("🔍 Running escalation check...")
    run_escalation()
    print("✅ Done")