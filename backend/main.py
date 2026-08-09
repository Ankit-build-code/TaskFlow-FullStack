"""
main.py — TaskFlow FastAPI application with JWT Security & Authorization.
"""

import time
import logging
from typing import Optional, List
from datetime import datetime, timedelta

from fastapi import FastAPI, Depends, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import func
import bcrypt
from jose import JWTError, jwt

from backend.database import engine, SessionLocal
from backend.models import Base, User, Project, Task
from backend.schemas import (
    UserCreate, UserResponse,
    ProjectCreate, ProjectResponse,
    TaskCreate, TaskUpdate, TaskResponse,
    ProjectStats, QuickAddRequest,
    Token, TokenData
)
from backend.algorithms import insertion_sort, binary_search, linear_search
from backend.ai_parser import parse_task_description

# ─────────────────────────────────────────────────────────────────
# Security & Auth Configuration
# ─────────────────────────────────────────────────────────────────

SECRET_KEY = "CHANGE_THIS_TO_A_SECURE_RANDOM_SECRET_KEY_IN_PRODUCTION"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def get_password_hash(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# ─────────────────────────────────────────────────────────────────
# Logging & Database Initialization
# ─────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
logger = logging.getLogger("taskflow")

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="TaskFlow API",
    description="Secure Task and project management platform.",
    version="1.0.0",
)

# Explicit CORS configuration (Restricting wildcard for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://taskflow-theta-six-59.vercel.app", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


# Shared DB Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Auth Dependency: Fetch Currently Authenticated User
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user


# ═══════════════════════════════════════════════════════════════════
# AUTH & USER endpoints
# ═══════════════════════════════════════════════════════════════════

@app.post("/users", response_model=UserResponse, status_code=201, tags=["users"])
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    """User Registration."""
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="A user with that email already exists.")
    
    hashed_pwd = get_password_hash(payload.password)
    user = User(name=payload.name, email=payload.email, hashed_password=hashed_pwd)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/token", response_model=Token, tags=["auth"])
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """OAuth2 token login route."""
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/users/me", response_model=UserResponse, tags=["users"])
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Return current logged-in user profile."""
    return current_user


# ═══════════════════════════════════════════════════════════════════
# PROJECT endpoints (Protected + Ownership verification)
# ═══════════════════════════════════════════════════════════════════

@app.post("/projects", response_model=ProjectResponse, status_code=201, tags=["projects"])
def create_project(
    payload: ProjectCreate, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    project = Project(
        name=payload.name,
        description=payload.description,
        owner_id=current_user.id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@app.get("/projects", response_model=List[ProjectResponse], tags=["projects"])
def list_projects(
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Return projects belonging to current user only."""
    return db.query(Project).filter(Project.owner_id == current_user.id).all()


@app.get("/projects/{project_id}", response_model=ProjectResponse, tags=["projects"])
def get_project(
    project_id: int, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(
        Project.id == project_id, 
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found or unauthorized.")
    return project


@app.delete("/projects/{project_id}", status_code=204, tags=["projects"])
def delete_project(
    project_id: int, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(
        Project.id == project_id, 
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found or unauthorized.")
    db.delete(project)
    db.commit()
    return None


# ═══════════════════════════════════════════════════════════════════
# STATISTICS endpoint
# ═══════════════════════════════════════════════════════════════════

@app.get("/projects/{project_id}/stats", response_model=ProjectStats, tags=["projects"])
def project_stats(
    project_id: int, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(
        Project.id == project_id, 
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

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


# ═══════════════════════════════════════════════════════════════════
# TASK endpoints (Protected + Search & Sort)
# ═══════════════════════════════════════════════════════════════════

_PRIORITY_RANK = {"low": 1, "medium": 2, "high": 3}


@app.get("/tasks/search", tags=["tasks", "algorithms"])
def search_tasks(
    title: str = Query(...),
    algo: str = Query(default="binary"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tasks_db = db.query(Task).join(Project).filter(Project.owner_id == current_user.id).all()
    index = [{"id": t.id, "title": t.title} for t in tasks_db]

    if algo == "binary":
        insertion_sort(index, "title")
        found_idx = binary_search(index, title, "title")
    else:
        found_idx = linear_search(index, title, "title")

    if found_idx == -1:
        raise HTTPException(status_code=404, detail=f"No task with title '{title}' found.")

    task_id = index[found_idx]["id"]
    task = db.query(Task).filter(Task.id == task_id).first()
    return TaskResponse.model_validate(task)


@app.post("/tasks/quick-add", response_model=TaskResponse, status_code=201, tags=["tasks", "ai"])
def quick_add_task(
    payload: QuickAddRequest, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(
        Project.id == payload.project_id, 
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found or unauthorized.")

    parsed = parse_task_description(payload.description)
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


@app.post("/tasks", response_model=TaskResponse, status_code=201, tags=["tasks"])
def create_task(
    payload: TaskCreate, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(
        Project.id == payload.project_id, 
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found or unauthorized.")

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
    project_id: Optional[int] = Query(default=None),
    sort: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Task).join(Project).filter(Project.owner_id == current_user.id)
    if project_id is not None:
        query = query.filter(Task.project_id == project_id)
    tasks = query.all()

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
        insertion_sort(records, "_priority_rank")
    elif sort == "due_date":
        insertion_sort(records, "due_date")

    for r in records:
        r.pop("_priority_rank", None)

    return [TaskResponse(**r) for r in records]


@app.get("/tasks/{task_id}", response_model=TaskResponse, tags=["tasks"])
def get_task(
    task_id: int, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    task = db.query(Task).join(Project).filter(
        Task.id == task_id, 
        Project.owner_id == current_user.id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found or unauthorized.")
    return task


@app.put("/tasks/{task_id}", response_model=TaskResponse, tags=["tasks"])
def update_task(
    task_id: int, 
    payload: TaskUpdate, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    task = db.query(Task).join(Project).filter(
        Task.id == task_id, 
        Project.owner_id == current_user.id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found or unauthorized.")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)

    db.commit()
    db.refresh(task)
    return task


@app.delete("/tasks/{task_id}", status_code=204, tags=["tasks"])
def delete_task(
    task_id: int, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    task = db.query(Task).join(Project).filter(
        Task.id == task_id, 
        Project.owner_id == current_user.id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found or unauthorized.")
    db.delete(task)
    db.commit()
    return None


# ─────────────────────────────────────────────────────────────────
# Health Check
# ─────────────────────────────────────────────────────────────────

@app.get("/health", tags=["system"])
def health():
    return {"status": "ok", "app": "TaskFlow"}