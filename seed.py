"""
seed.py — Seed the TaskFlow database with realistic task data.

Creates:
  - 2 users
  - 3 projects (owned by the users)
  - N tasks distributed across the projects

Default seed sizes: 10, 500, 3000 tasks (three snapshots for benchmark).
Run once per size:
    python seed.py           # seeds 3000 tasks (default)
    python seed.py 500       # seeds 500 tasks
    python seed.py 10        # seeds 10 tasks
    python seed.py clear     # deletes all rows (keeps schema)
"""

import sys
import os
import random

# ── allow import from backend/ when running from repo root ──────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from database import engine, SessionLocal
from models import Base, User, Project, Task

# ─────────────────────────────────────────────────────────────────
# Ensure tables exist
# ─────────────────────────────────────────────────────────────────
Base.metadata.create_all(bind=engine)

# ─────────────────────────────────────────────────────────────────
# Sample data pools
# ─────────────────────────────────────────────────────────────────
PRIORITIES  = ["low", "medium", "high"]
STATUSES    = ["todo", "in_progress", "done"]
DUE_DATES   = [
    "today", "tomorrow", "next week", "next friday", "next monday",
    "2024-12-15", "2024-12-31", "2025-01-10", "2025-02-28", None,
]

TASK_TITLES = [
    "Review pull request for order-routing service",
    "Fix latency spike in dark-store inventory API",
    "Write integration tests for payment gateway",
    "Update dependency versions in requirements.txt",
    "Refactor warehouse allocation algorithm",
    "Deploy canary release to prod cluster",
    "Profile and optimise database query N+1",
    "Add OpenTelemetry tracing to delivery service",
    "Design schema for real-time demand forecasting",
    "Implement circuit breaker in fulfillment service",
    "Document onboarding runbook for new engineers",
    "Rotate expired TLS certificates",
    "Investigate memory leak in notification worker",
    "Build admin dashboard for ops team",
    "Add rate limiting to external partner API",
    "Create Grafana dashboard for SLA metrics",
    "Implement idempotency keys for order creation",
    "Set up PagerDuty escalation policy",
    "Write post-mortem for last week's outage",
    "Migrate Redis cache to cluster mode",
    "Add dark-store capacity constraints to routing",
    "Benchmark gRPC vs REST for internal services",
    "Implement task retry with exponential back-off",
    "Enable feature flag for new checkout flow",
    "Audit IAM roles and least-privilege access",
    "Reduce cold-start time of Lambda functions",
    "Automate DB backup verification job",
    "Implement soft-delete for order records",
    "Add pagination to product catalogue endpoint",
    "Investigate high CPU on worker pods",
]


def _make_title(i: int) -> str:
    """Generate a unique title by cycling through TASK_TITLES and appending a counter."""
    base = TASK_TITLES[i % len(TASK_TITLES)]
    suffix = f" #{i + 1}"
    return base + suffix


def clear_data(db):
    db.query(Task).delete()
    db.query(Project).delete()
    db.query(User).delete()
    db.commit()
    print("Cleared all rows.")


def seed(n: int):
    db = SessionLocal()
    try:
        # ── Users ────────────────────────────────────────────────
        user1 = db.query(User).filter_by(email="alice@blinkit.com").first()
        if not user1:
            user1 = User(name="Alice Sharma", email="alice@blinkit.com")
            db.add(user1)
        user2 = db.query(User).filter_by(email="bob@blinkit.com").first()
        if not user2:
            user2 = User(name="Bob Verma", email="bob@blinkit.com")
            db.add(user2)
        db.flush()  # assigns IDs without committing

        # ── Projects ──────────────────────────────────────────────
        project_data = [
            ("Sprint 12 — Inventory", user1.id),
            ("Sprint 12 — Delivery", user1.id),
            ("Infra & Reliability Q4", user2.id),
        ]
        project_objs = []
        for pname, oid in project_data:
            p = db.query(Project).filter_by(name=pname).first()
            if not p:
                p = Project(name=pname, owner_id=oid)
                db.add(p)
            project_objs.append(p)
        db.flush()

        project_ids = [p.id for p in project_objs]

        # ── Tasks ──────────────────────────────────────────────────
        random.seed(99)
        tasks_added = 0
        for i in range(n):
            task = Task(
                title=_make_title(i),
                description=None,
                priority=random.choice(PRIORITIES),
                due_date=random.choice(DUE_DATES),
                status=random.choice(STATUSES),
                project_id=random.choice(project_ids),
            )
            db.add(task)
            tasks_added += 1

            # Flush in batches to avoid holding too many objects in memory
            if tasks_added % 500 == 0:
                db.flush()
                print(f"  {tasks_added}/{n} tasks staged…")

        db.commit()
        total_tasks = db.query(Task).count()
        print(f"Seeding complete. Total tasks in DB: {total_tasks}")

    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "3000"

    if arg.lower() == "clear":
        db = SessionLocal()
        try:
            clear_data(db)
        finally:
            db.close()
    else:
        try:
            n = int(arg)
        except ValueError:
            print(f"Usage: python seed.py [10|500|3000|clear]")
            sys.exit(1)

        print(f"Seeding {n:,} tasks into taskflow.db …")
        seed(n)
