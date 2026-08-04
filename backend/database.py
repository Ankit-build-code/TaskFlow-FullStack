"""
Database engine and session factory for TaskFlow.
Uses SQLite by default (no external database required).
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# SQLite file stored in the backend directory
DATABASE_URL = "sqlite:///./taskflow.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # needed for SQLite + FastAPI threads
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
