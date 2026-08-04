"""
database.py — Database engine and session factory for TaskFlow.
Reads DATABASE_URL from .env file (Supabase PostgreSQL).
Falls back to local SQLite if DATABASE_URL is not set.
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

# Load .env from the backend/ directory
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./taskflow.db")

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )

    # Force search_path = public on every connection so
    # SQLAlchemy creates and queries tables in the right schema
    @event.listens_for(engine, "connect")
    def set_search_path(dbapi_conn, conn_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("SET search_path TO public")
        dbapi_conn.commit()
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
