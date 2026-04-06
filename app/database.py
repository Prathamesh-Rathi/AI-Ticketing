# backend/app/database.py

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import DATABASE_URL

# Create the SQLite engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # needed for SQLite only
)

# Each request gets its own session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# All models will inherit from this
Base = declarative_base()

# Dependency — used in every router to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()