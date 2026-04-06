# backend/app/schemas.py
# Pydantic schemas — used for request/response validation

from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# ─────────────────────────────────────────────
# DEPARTMENT SCHEMAS
# ─────────────────────────────────────────────

class DepartmentCreate(BaseModel):
    name: str
    description: Optional[str] = None

class DepartmentOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

# ─────────────────────────────────────────────
# EMPLOYEE SCHEMAS
# ─────────────────────────────────────────────

class EmployeeCreate(BaseModel):
    name: str
    email: str
    role: str
    department_id: int
    skill_tags: Optional[str] = ""
    availability: Optional[str] = "Available"

class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    skill_tags: Optional[str] = None
    availability: Optional[str] = None
    is_active: Optional[bool] = None

class EmployeeOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    department_id: int
    skill_tags: str
    avg_resolution_time: float
    current_ticket_load: int
    availability: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# ─────────────────────────────────────────────
# TICKET SCHEMAS
# ─────────────────────────────────────────────

class TicketCreate(BaseModel):
    title: str
    body: str
    submitter_name: str
    submitter_email: str

class TicketStatusUpdate(BaseModel):
    status: str
    note: Optional[str] = None
    actor: str = "System"

class TicketAssign(BaseModel):
    employee_id: int
    actor: str = "Admin"

# ─────────────────────────────────────────────
# AI ANALYSIS SCHEMA
# ─────────────────────────────────────────────

class AIAnalysisOut(BaseModel):
    category: str
    summary: str
    severity: str
    resolution_path: str
    sentiment: str
    suggested_department: Optional[str]
    suggested_employee: Optional[str]
    confidence_score: int
    estimated_resolution_time: Optional[str]
    auto_response: Optional[str]
    routing_reason: Optional[str]

    class Config:
        from_attributes = True

# ─────────────────────────────────────────────
# TICKET LOG SCHEMA
# ─────────────────────────────────────────────

class TicketLogOut(BaseModel):
    id: int
    actor: str
    action: str
    note: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

# ─────────────────────────────────────────────
# FEEDBACK SCHEMA
# ─────────────────────────────────────────────

class FeedbackCreate(BaseModel):
    helpful: bool
    comment: Optional[str] = None

class FeedbackOut(BaseModel):
    helpful: bool
    comment: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

# ─────────────────────────────────────────────
# FULL TICKET DETAIL (with all relations)
# ─────────────────────────────────────────────

class TicketOut(BaseModel):
    id: int
    title: str
    body: str
    submitter_name: str
    submitter_email: str
    status: str
    department_id: Optional[int]
    assignee_id: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]
    resolved_at: Optional[datetime]
    ai_analysis: Optional[AIAnalysisOut]
    logs: List[TicketLogOut] = []
    feedback: Optional[FeedbackOut]

    class Config:
        from_attributes = True