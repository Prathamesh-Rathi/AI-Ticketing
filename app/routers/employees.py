# backend/app/routers/employees.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app import models
from app.schemas import EmployeeCreate, EmployeeUpdate, EmployeeOut, DepartmentCreate, DepartmentOut

router = APIRouter(prefix="/api", tags=["Employees & Departments"])


# ─────────────────────────────────────────────
# DEPARTMENT ENDPOINTS
# ─────────────────────────────────────────────

@router.post("/departments/", response_model=DepartmentOut)
def create_department(payload: DepartmentCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Department).filter(
        models.Department.name == payload.name
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Department already exists")

    dept = models.Department(name=payload.name, description=payload.description)
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return dept


@router.get("/departments/", response_model=List[DepartmentOut])
def list_departments(db: Session = Depends(get_db)):
    return db.query(models.Department).all()


# ─────────────────────────────────────────────
# EMPLOYEE ENDPOINTS
# ─────────────────────────────────────────────

@router.post("/employees/", response_model=EmployeeOut)
def create_employee(payload: EmployeeCreate, db: Session = Depends(get_db)):
    dept = db.query(models.Department).filter(
        models.Department.id == payload.department_id
    ).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")

    existing = db.query(models.Employee).filter(
        models.Employee.email == payload.email
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Employee with this email already exists")

    employee = models.Employee(
        name=payload.name,
        email=payload.email,
        role=payload.role,
        department_id=payload.department_id,
        skill_tags=payload.skill_tags,
        availability=payload.availability
    )
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee


@router.get("/employees/", response_model=List[EmployeeOut])
def list_employees(db: Session = Depends(get_db)):
    return db.query(models.Employee).filter(models.Employee.is_active == True).all()


@router.get("/employees/{employee_id}", response_model=EmployeeOut)
def get_employee(employee_id: int, db: Session = Depends(get_db)):
    emp = db.query(models.Employee).filter(models.Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    return emp


@router.patch("/employees/{employee_id}", response_model=EmployeeOut)
def update_employee(employee_id: int, payload: EmployeeUpdate, db: Session = Depends(get_db)):
    emp = db.query(models.Employee).filter(models.Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(emp, key, value)

    db.commit()
    db.refresh(emp)
    return emp


@router.delete("/employees/{employee_id}")
def deactivate_employee(employee_id: int, db: Session = Depends(get_db)):
    emp = db.query(models.Employee).filter(models.Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    emp.is_active = False
    db.commit()
    return {"message": f"Employee {emp.name} deactivated"}