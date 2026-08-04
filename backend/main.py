"""
main.py — TaskFlow FastAPI application.

Sections covered
----------------
Section 1 : CRUD endpoints for users, projects, tasks.
            Statistics endpoint (SQL aggregation).
            Middleware (request logging).
            CORS configuration.
            Shared DB dependency (Depends).

Section 2 : GET /tasks?sort=priority  — uses insertion_sort
            GET /tasks/search         — uses binary_search / linear_search

Section 3 : POST /tasks/quick-add     — uses mock_parse (or optional real LLM)
"""

import time
import logging
from typing import Optional, List

from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import engine, SessionLocal
from models import Base, User, Project, Task
from schemas import (
    UserCreate, UserResponse,
    ProjectCreate, ProjectResponse,
    TaskCreate, TaskUpdate, TaskResponse,
    ProjectStats, QuickAddRequest,
)
from algorithms import insertion_sort, binary_search, linear_search
from ai_parser import parse_task_description

# ─────────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
logger = logging.getLogger("taskflow")

# ─────────────────────────────────────────────────────────────────
# Database initialisation
# ─────────────────────────────────────────────────────────────────

Base.metadata.create_all(bind=engine)

# ─────────────────────────────────────────────────────────────────
# App + CORS
# ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title="TaskFlow API",
    description="Task and project management platform for Blinkit engineering pods.",
    version="1.0.0",
)

# CORS: allow the frontend's local development origins explicitly.
# Adjust origins if you serve the frontend from a different port.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "null",           # allows file:// origin when opened directly in a browser
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
)

# ─────────────────────────────────────────────────────────────────
# Custom middleware — logs method, path, and processing time (ms)
# ─────────────────────────────────────────────────────────────────

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start) * 1000
    logger.info(
        "%s %s  →  %d  (%.1f ms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response

# ─────────────────────────────────────────────────────────────────
# Shared database dependency (Section 1, Task 6)
# Used in every endpoint function below — written once, reused everywhere.
# ─────────────────────────────────────────────────────────────────

def get_db():
    """Yield a SQLAlchemy session and guarantee it is closed after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════════
# USER endpoints
# ═══════════════════════════════════════════════════════════════════

@app.post("/users", response_model=UserResponse, status_code=201, tags=["users"])
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    """Create a new user. Returns 422 if email is already taken (Pydantic/DB)."""
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="A user with that email already exists.")
    user = User(name=payload.name, email=payload.email)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.get("/users", response_model=List[UserResponse], tags=["users"])
def list_users(db: Session = Depends(get_db)):
    """Return all users."""
    return db.query(User).all()


@app.get("/users/{user_id}", response_model=UserResponse, tags=["users"])
def get_user(user_id: int, db: Session = Depends(get_db)):
    """Return a single user by id, or 404."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found.")
    return user


# ═══════════════════════════════════════════════════════════════════
# PROJECT endpoints
# ═══════════════════════════════════════════════════════════════════

@app.post("/projects", response_model=ProjectResponse, status_code=201, tags=["projects"])
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    """Create a new project owned by an existing user."""
    owner = db.query(User).filter(User.id == payload.owner_id).first()
    if not owner:
        raise HTTPException(status_code=404, detail=f"User {payload.owner_id} not found.")
    project = Project(
        name=payload.name,
        description=payload.description,
        owner_id=payload.owner_id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@app.get("/projects", response_model=List[ProjectResponse], tags=["projects"])
def list_projects(db: Session = Depends(get_db)):
    """Return all projects."""
    return db.query(Project).all()


@app.get("/projects/{project_id}", response_model=ProjectResponse, tags=["projects"])
def get_project(project_id: int, db: Session = Depends(get_db)):
    """Return a single project by id, or 404."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found.")
    return project


# ═══════════════════════════════════════════════════════════════════
# STATISTICS endpoint (Section 1, Task 5)
# SQL aggregation — COUNT + GROUP BY executed in the query, not in Python.
# ═══════════════════════════════════════════════════════════════════

@app.get("/projects/{project_id}/stats", response_model=ProjectStats, tags=["projects"])
def project_stats(project_id: int, db: Session = Depends(get_db)):
    """
    Return per-project task statistics using SQL aggregation.
    The COUNT and GROUP BY happen inside the database query, not in Python.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found.")

    # SQL aggregation: count tasks grouped by status in one query
    rows = (
        db.query(Task.status, func.count(Task.id).label("cnt"))
        .filter(Task.project_id == project_id)
        .group_by(Task.status)
        .all()
    )

    status_counts = {row.status: row.cnt for row in rows}
    total = sum(status_counts.values())

    return ProjectStats(
        project_id=project.id,
        project_name=project.name,
        total_tasks=total,
        todo_count=status_counts.get("todo", 0),
        in_progress_count=status_counts.get("in_progress", 0),
        done_count=status_counts.get("done", 0),
    )


@app.get("/stats", response_model=List[ProjectStats], tags=["projects"])
def all_project_stats(db: Session = Depends(get_db)):
    """Return task statistics for every project."""
    projects = db.query(Project).all()
    stats = []
    for project in projects:
        rows = (
            db.query(Task.status, func.count(Task.id).label("cnt"))
            .filter(Task.project_id == project.id)
            .group_by(Task.status)
            .all()
        )
        status_counts = {row.status: row.cnt for row in rows}
        total = sum(status_counts.values())
        stats.append(ProjectStats(
            project_id=project.id,
            project_name=project.name,
            total_tasks=total,
            todo_count=status_counts.get("todo", 0),
            in_progress_count=status_counts.get("in_progress", 0),
            done_count=status_counts.get("done", 0),
        ))
    return stats


# ═══════════════════════════════════════════════════════════════════
# TASK endpoints  (Section 1 CRUD + Section 2 sort/search)
# NOTE: /tasks/search and /tasks/quick-add MUST be declared BEFORE
#       /tasks/{task_id} so FastAPI doesn't treat "search" or
#       "quick-add" as an integer task_id.
# ═══════════════════════════════════════════════════════════════════

# ── Section 2: Search ────────────────────────────────────────────

@app.get("/tasks/search", tags=["tasks", "algorithms"])
def search_tasks(
    title: str = Query(..., description="Exact title to search for"),
    algo: str = Query(default="binary", description="'binary' or 'linear'"),
    db: Session = Depends(get_db),
):
    """
    Search for a task by exact title.

    algo=binary  → binary_search on a title-sorted index (via insertion_sort).
    algo=linear  → linear_search on the unsorted index.

    Returns the matching task (200) or 404 if no task has that exact title.
    """
    # Build in-memory index from real DB rows
    tasks_db = db.query(Task).all()
    index = [{"id": t.id, "title": t.title} for t in tasks_db]

    if algo == "binary":
        # Sort the index by title using our insertion_sort, then binary_search
        insertion_sort(index, "title")
        found_idx = binary_search(index, title, "title")
    else:
        # Linear search over unsorted index
        found_idx = linear_search(index, title, "title")

    if found_idx == -1:
        raise HTTPException(status_code=404, detail=f"No task with title '{title}' found.")

    task_id = index[found_idx]["id"]
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")
    return TaskResponse.model_validate(task)


# ── Section 3: Quick-Add ─────────────────────────────────────────

@app.post("/tasks/quick-add", response_model=TaskResponse, status_code=201, tags=["tasks", "ai"])
def quick_add_task(payload: QuickAddRequest, db: Session = Depends(get_db)):
    """
    Accept a plain-English description and create a structured task row.

    The parser (mock by default, real LLM when USE_REAL_LLM=1) extracts:
      - title        (stripped description)
      - priority     (low / medium / high)
      - due_date     (matched date phrase or null)

    The resulting record is validated against TaskCreate before being persisted.
    Returns 422 if project_id does not reference an existing project.
    """
    # Verify project exists first
    project = db.query(Project).filter(Project.id == payload.project_id).first()
    if not project:
        raise HTTPException(
            status_code=422,
            detail=f"project_id {payload.project_id} does not reference an existing project.",
        )

    # Parse description using the mock (or optional real LLM)
    parsed = parse_task_description(payload.description)

    # Validate via Pydantic before writing to DB
    task_in = TaskCreate(
        title=parsed["title"],
        priority=parsed["priority"],
        due_date=parsed.get("due_date_hint"),
        status="todo",
        project_id=payload.project_id,
    )

    task = Task(
        title=task_in.title,
        description=None,
        priority=task_in.priority,
        due_date=task_in.due_date,
        status=task_in.status,
        project_id=task_in.project_id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


# ── Section 1: Task CRUD + Section 2: Sort ───────────────────────

# Priority sort rank used by Section 2's sort endpoint
_PRIORITY_RANK = {"low": 1, "medium": 2, "high": 3}


@app.post("/tasks", response_model=TaskResponse, status_code=201, tags=["tasks"])
def create_task(payload: TaskCreate, db: Session = Depends(get_db)):
    """Create a new task. Returns 404 if project_id is not found."""
    project = db.query(Project).filter(Project.id == payload.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {payload.project_id} not found.")

    task = Task(
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        due_date=payload.due_date,
        status=payload.status,
        project_id=payload.project_id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@app.get("/tasks", response_model=List[TaskResponse], tags=["tasks"])
def list_tasks(
    project_id: Optional[int] = Query(default=None, description="Filter by project"),
    sort: Optional[str] = Query(default=None, description="Sort field: 'priority' or 'due_date'"),
    db: Session = Depends(get_db),
):
    """
    List tasks, optionally filtered by project.

    sort=priority : fetches tasks from DB, maps priority → numeric rank,
                    then calls insertion_sort (Section 2) — NOT ORDER BY.
    sort=due_date : fetches tasks from DB, calls insertion_sort by due_date.
    """
    query = db.query(Task)
    if project_id is not None:
        query = query.filter(Task.project_id == project_id)
    tasks = query.all()

    # Convert to list of dicts for sorting
    records = [
        {
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "priority": t.priority,
            "due_date": t.due_date or "",
            "status": t.status,
            "project_id": t.project_id,
            "_priority_rank": _PRIORITY_RANK.get(t.priority, 2),
        }
        for t in tasks
    ]

    if sort == "priority":
        # insertion_sort on numeric rank field (Section 2 engine)
        insertion_sort(records, "_priority_rank")
    elif sort == "due_date":
        insertion_sort(records, "due_date")

    # Strip internal helper field before returning
    for r in records:
        r.pop("_priority_rank", None)

    return [TaskResponse(**r) for r in records]


@app.get("/tasks/{task_id}", response_model=TaskResponse, tags=["tasks"])
def get_task(task_id: int, db: Session = Depends(get_db)):
    """Return a single task by id, or 404."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found.")
    return task


@app.put("/tasks/{task_id}", response_model=TaskResponse, tags=["tasks"])
def update_task(task_id: int, payload: TaskUpdate, db: Session = Depends(get_db)):
    """Full update of a task (fields absent from payload are left unchanged)."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found.")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)

    db.commit()
    db.refresh(task)
    return task


@app.delete("/tasks/{task_id}", status_code=204, tags=["tasks"])
def delete_task(task_id: int, db: Session = Depends(get_db)):
    """Delete a task by id, or 404."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found.")
    db.delete(task)
    db.commit()
    return None


# ─────────────────────────────────────────────────────────────────
# Health check
# ─────────────────────────────────────────────────────────────────

@app.get("/health", tags=["system"])
def health():
    return {"status": "ok", "app": "TaskFlow"}
