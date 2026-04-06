# backend/app/models.py

from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum

# ─────────────────────────────────────────────
# ENUMS
# ─────────────────────────────────────────────

class TicketStatus(str, enum.Enum):
    new = "New"
    assigned = "Assigned"
    in_progress = "In Progress"
    pending_info = "Pending Info"
    resolved = "Resolved"
    closed = "Closed"

class TicketSeverity(str, enum.Enum):
    critical = "Critical"
    high = "High"
    medium = "Medium"
    low = "Low"

class TicketCategory(str, enum.Enum):
    billing = "Billing"
    bug = "Bug"
    access = "Access"
    hr = "HR"
    server = "Server"
    db = "DB"
    feature = "Feature"
    other = "Other"

class ResolutionPath(str, enum.Enum):
    auto = "Auto-resolve"
    assign = "Assign"

class Sentiment(str, enum.Enum):
    frustrated = "Frustrated"
    neutral = "Neutral"
    polite = "Polite"

class Availability(str, enum.Enum):
    available = "Available"
    busy = "Busy"
    on_leave = "On Leave"

# ─────────────────────────────────────────────
# TABLE 1 — DEPARTMENTS
# ─────────────────────────────────────────────

class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    employees = relationship("Employee", back_populates="department")
    tickets = relationship("Ticket", back_populates="department")

# ─────────────────────────────────────────────
# TABLE 2 — EMPLOYEES
# ─────────────────────────────────────────────

class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    role = Column(String(100), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    skill_tags = Column(Text, default="")        # comma-separated: "Python,Database,Networking"
    avg_resolution_time = Column(Float, default=0.0)  # in hours
    current_ticket_load = Column(Integer, default=0)
    availability = Column(String(20), default="Available")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    department = relationship("Department", back_populates="employees")
    assigned_tickets = relationship("Ticket", back_populates="assignee")

# ─────────────────────────────────────────────
# TABLE 3 — TICKETS
# ─────────────────────────────────────────────

class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)

    # Submitted by user
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    submitter_name = Column(String(100), nullable=False)
    submitter_email = Column(String(150), nullable=False)

    # Status & routing
    status = Column(String(30), default="New")
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    assignee_id = Column(Integer, ForeignKey("employees.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    department = relationship("Department", back_populates="tickets")
    assignee = relationship("Employee", back_populates="assigned_tickets")
    ai_analysis = relationship("AIAnalysis", back_populates="ticket", uselist=False)
    logs = relationship("TicketLog", back_populates="ticket")
    feedback = relationship("Feedback", back_populates="ticket", uselist=False)

# ─────────────────────────────────────────────
# TABLE 4 — AI ANALYSIS
# ─────────────────────────────────────────────

class AIAnalysis(Base):
    __tablename__ = "ai_analysis"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), unique=True, nullable=False)

    # Structured AI output
    category = Column(String(50), nullable=False)
    summary = Column(Text, nullable=False)
    severity = Column(String(20), nullable=False)
    resolution_path = Column(String(20), nullable=False)
    sentiment = Column(String(20), nullable=False)
    suggested_department = Column(String(100), nullable=True)
    suggested_employee = Column(String(100), nullable=True)
    confidence_score = Column(Integer, nullable=False)          # 0-100
    estimated_resolution_time = Column(String(50), nullable=True)
    auto_response = Column(Text, nullable=True)                 # filled if auto-resolved
    routing_reason = Column(Text, nullable=True)                # why routed to X

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship
    ticket = relationship("Ticket", back_populates="ai_analysis")

# ─────────────────────────────────────────────
# TABLE 5 — TICKET LOGS (audit trail)
# ─────────────────────────────────────────────

class TicketLog(Base):
    __tablename__ = "ticket_logs"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    actor = Column(String(100), nullable=False)     # who did the action
    action = Column(String(100), nullable=False)    # e.g. "Status changed to In Progress"
    note = Column(Text, nullable=True)              # optional internal note
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    ticket = relationship("Ticket", back_populates="logs")

# ─────────────────────────────────────────────
# TABLE 6 — FEEDBACK
# ─────────────────────────────────────────────

class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), unique=True, nullable=False)
    helpful = Column(Boolean, nullable=False)       # True = Yes, False = No
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    ticket = relationship("Ticket", back_populates="feedback")