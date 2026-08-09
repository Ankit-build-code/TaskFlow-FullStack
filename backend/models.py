"""
SQLAlchemy ORM models for TaskFlow.
Three tables: users, projects, tasks with appropriate constraints and relationships.
"""

from sqlalchemy import (
    Column, Integer, String, Text, ForeignKey, CheckConstraint, UniqueConstraint
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(200), nullable=False, unique=True)
    hashed_password = Column(String(255), nullable=False)  # Password hash storage

    # One user owns many projects
    projects = relationship("Project", back_populates="owner", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User id={self.id} email={self.email!r}>"


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Many projects belong to one user
    owner = relationship("User", back_populates="projects")
    # One project contains many tasks
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Project id={self.id} name={self.name!r}>"


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint(
            "priority IN ('low', 'medium', 'high')",
            name="ck_tasks_priority"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    # Closed set: low / medium / high
    priority = Column(String(10), nullable=False, default="medium")
    # Stored as raw text (can hold "next friday", "2024-12-31", etc.)
    due_date = Column(String(100), nullable=True)
    status = Column(String(50), nullable=False, default="todo")
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)

    # Many tasks belong to one project
    project = relationship("Project", back_populates="tasks")

    def __repr__(self):
        return f"<Task id={self.id} title={self.title!r} priority={self.priority!r}>"