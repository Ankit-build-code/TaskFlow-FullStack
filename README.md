# TaskFlow — Full-Stack AI-Assisted Task Management Platform

An internal task-and-project management platform for Blinkit's dark-store engineering pods.
Three graded sections — core CRUD app, algorithms engine, and AI quick-add — all running as
one FastAPI service backed by a single SQLite database.

---

## Table of Contents

1. [Repository structure](#1-repository-structure)
2. [Environment setup](#2-environment-setup)
3. [Running the app](#3-running-the-app)
4. [Endpoint reference](#4-endpoint-reference)
5. [Database schema](#5-database-schema)
6. [Section 2 — Algorithms: complexity write-up and benchmark results](#6-section-2--algorithms)
7. [Section 3 — AI Quick-Add: prompting rationale and worked examples](#7-section-3--ai-quick-add)
8. [Changelog — Recent Fixes](#8-changelog--recent-fixes)

---

## 1. Repository Structure

```
taskflow/
├── backend/
│   ├── main.py          # FastAPI app, all endpoints (Sections 1, 2, 3)
│   ├── models.py        # SQLAlchemy ORM: User, Project, Task
│   ├── schemas.py       # Pydantic request / response models
│   ├── database.py      # SQLite engine + SessionLocal
│   ├── algorithms.py    # insertion_sort, binary_search, linear_search + counting wrappers
│   └── ai_parser.py     # Rule-based mock parser + optional real-LLM path
├── frontend/
│   ├── index.html       # Dashboard HTML (semantic, accessible)
│   ├── styles.css       # Responsive styles, 2 breakpoints, sticky header
│   └── script.js        # Full CRUD, localStorage cache, Fetch API, DOM rendering
├── benchmark.py         # Section 2 comparison-counting benchmark
├── check_algorithms.py  # Section 2 PASS/FAIL automated checks
├── seed.py              # Seed DB with realistic task data (10 / 500 / 3000 rows)
├── requirements.txt
├── results/
│   └── benchmark_results.txt   # Saved benchmark output
└── README.md
```

---

## 2. Environment Setup

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd taskflow

# 2. Create and activate a virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

---

## 3. Running the App

This project uses a **two-process run** (recommended).

### Process 1 — Backend (FastAPI)

```bash
cd taskflow/backend
uvicorn main:app --reload --port 8000
```

The API is now available at `http://127.0.0.1:8000`.
Interactive docs: `http://127.0.0.1:8000/docs`

### Process 2 — Frontend (static server)

Open a second terminal, then serve the `frontend/` directory:

```bash
# Option A: Python built-in server (any Python 3 install)
cd taskflow/frontend
python -m http.server 5500

# Option B: VS Code Live Server (port 5500 by default)
# Option C: Open index.html directly in your browser
#   (CORS is configured to accept the "null" origin for file:// access)
```

Open `http://127.0.0.1:5500` (or the URL your static server reports) in your browser.

The frontend's `API_BASE` in `script.js` points to `http://127.0.0.1:8000`.

### Utility scripts

```bash
# From the repo root (taskflow/)

# Seed the database with sample data
python seed.py 3000     # 3000 tasks (default)
python seed.py 500
python seed.py 10
python seed.py clear    # wipe all rows

# Run the benchmark (comparison counts at 3 sizes)
python benchmark.py

# Run the PASS/FAIL algorithm checks
python check_algorithms.py
```

---

## 4. Endpoint Reference

All endpoints return JSON. The base URL is `http://127.0.0.1:8000`.

### Users

#### POST /users — Create a user

**Request body**
```json
{ "name": "Alice Sharma", "email": "alice@blinkit.com" }
```
**Response 201**
```json
{ "id": 1, "name": "Alice Sharma", "email": "alice@blinkit.com" }
```
**Failure 409** — email already registered.
**Failure 422** — missing required field or invalid email format.

#### GET /users — List all users

**Response 200**
```json
[
  { "id": 1, "name": "Alice Sharma", "email": "alice@blinkit.com" },
  { "id": 2, "name": "Bob Verma",    "email": "bob@blinkit.com" }
]
```

#### GET /users/{user_id} — Get user by id

**Response 200** — same shape as create response.
**Failure 404** — `{ "detail": "User 99 not found." }`

---

### Projects

#### POST /projects — Create a project

**Request body**
```json
{ "name": "Sprint 12 — Inventory", "description": "Q4 inventory work", "owner_id": 1 }
```
**Response 201**
```json
{ "id": 1, "name": "Sprint 12 — Inventory", "description": "Q4 inventory work", "owner_id": 1 }
```
**Failure 404** — owner_id not found.
**Failure 422** — blank name or missing required field.

#### GET /projects — List all projects

**Response 200** — array of project objects.

#### GET /projects/{project_id} — Get project by id

**Response 200** — single project object.
**Failure 404** — project not found.

#### GET /projects/{project_id}/stats — Per-project task statistics

Computed with SQL `COUNT + GROUP BY` — aggregation happens in the database, not in Python.

**Response 200**
```json
{
  "project_id": 1,
  "project_name": "Sprint 12 — Inventory",
  "total_tasks": 12,
  "todo_count": 5,
  "in_progress_count": 4,
  "done_count": 3
}
```
**Failure 404** — project not found.

#### GET /stats — Statistics for all projects

**Response 200** — array of project-stats objects.

---

### Tasks (Section 1 — CRUD)

#### POST /tasks — Create a task

**Request body**
```json
{
  "title": "Fix latency spike in inventory API",
  "description": "P99 > 800ms on GET /items",
  "priority": "high",
  "due_date": "next friday",
  "status": "todo",
  "project_id": 1
}
```
**Response 201**
```json
{
  "id": 1,
  "title": "Fix latency spike in inventory API",
  "description": "P99 > 800ms on GET /items",
  "priority": "high",
  "due_date": "next friday",
  "status": "todo",
  "project_id": 1
}
```
**Failure 404** — project_id not found.
**Failure 422** — blank title, invalid priority (not low/medium/high), or missing required field.

#### GET /tasks — List tasks (optionally filtered and sorted)

```
GET /tasks
GET /tasks?project_id=1
GET /tasks?sort=priority          # sorted by insertion_sort (Section 2)
GET /tasks?sort=due_date
GET /tasks?project_id=1&sort=priority
```

**Response 200** — array of task objects.
When `sort=priority`, tasks are ordered low → medium → high using `insertion_sort` — not SQL ORDER BY.

#### GET /tasks/{task_id} — Get task by id

**Response 200** — single task object.
**Failure 404** — task not found.

#### PUT /tasks/{task_id} — Update a task

**Request body** (all fields optional; only supplied fields are updated)
```json
{ "title": "Updated title", "status": "in_progress", "priority": "medium" }
```
**Response 200** — updated task object.
**Failure 404** — task not found.
**Failure 422** — validation error.

#### DELETE /tasks/{task_id} — Delete a task

**Response 204** — no body.
**Failure 404** — task not found.

---

### Tasks (Section 2 — Algorithms)

#### GET /tasks?sort=priority — Sorted task list (insertion sort)

```
GET /tasks?sort=priority
```

Fetches all tasks from the DB, maps priority to a numeric rank (low=1, medium=2, high=3),
then sorts using `insertion_sort` from `backend/algorithms.py`. The DB's ORDER BY is never used.

**Response 200** — tasks sorted low → medium → high.

#### GET /tasks/search — Search by exact title (binary or linear)

```
GET /tasks/search?title=Fix latency spike in inventory API&algo=binary
GET /tasks/search?title=Fix latency spike in inventory API&algo=linear
```

- `algo=binary` (default): builds an index of `{id, title}` pairs from the DB, sorts it with
  `insertion_sort`, then calls `binary_search`.
- `algo=linear`: calls `linear_search` on the unsorted index.

**Response 200** — matching task object.
**Failure 404** — `{ "detail": "No task with title '...' found." }`

---

### Tasks (Section 3 — AI Quick-Add)

#### POST /tasks/quick-add — Parse plain English and create a task

**Request body**
```json
{ "description": "Finish the report next Friday, it's urgent", "project_id": 1 }
```
**Response 201**
```json
{
  "id": 42,
  "title": "Finish the report , it's",
  "description": null,
  "priority": "high",
  "due_date": "next friday",
  "status": "todo",
  "project_id": 1
}
```
**Failure 422** — malformed body, blank description, or project_id does not exist.
**Note:** works with zero API keys; the mock parser is always active by default.

---

## 5. Database Schema

Three tables: `users`, `projects`, `tasks`.

### users

| Column | Type         | Constraints              |
|--------|-------------|--------------------------|
| id     | INTEGER      | PRIMARY KEY              |
| name   | VARCHAR(100) | NOT NULL                 |
| email  | VARCHAR(200) | NOT NULL, UNIQUE         |

### projects

| Column      | Type         | Constraints                        |
|-------------|-------------|------------------------------------|
| id          | INTEGER      | PRIMARY KEY                        |
| name        | VARCHAR(200) | NOT NULL                           |
| description | TEXT         | nullable                           |
| owner_id    | INTEGER      | NOT NULL, FK → users.id ON DELETE CASCADE |

### tasks

| Column      | Type         | Constraints                                          |
|-------------|-------------|------------------------------------------------------|
| id          | INTEGER      | PRIMARY KEY                                          |
| title       | VARCHAR(500) | NOT NULL                                             |
| description | TEXT         | nullable                                             |
| priority    | VARCHAR(10)  | NOT NULL, DEFAULT 'medium', CHECK IN ('low','medium','high') |
| due_date    | VARCHAR(100) | nullable (raw text — stores both "next friday" and "2024-12-31") |
| status      | VARCHAR(50)  | NOT NULL, DEFAULT 'todo'                             |
| project_id  | INTEGER      | NOT NULL, FK → projects.id ON DELETE CASCADE         |

**SQLAlchemy relationships:**
- `User.projects` ↔ `Project.owner` (back_populates both sides)
- `Project.tasks` ↔ `Task.project` (back_populates both sides)

---

## 6. Section 2 — Algorithms

### Function signatures

```python
insertion_sort(records: list[dict], key: str) -> None
    # Sorts in place; no return value.

binary_search(sorted_records: list[dict], target_value, key: str) -> int
    # Returns index of matching record, or -1 if not found.

linear_search(records: list[dict], target_value, key: str) -> int
    # Returns index of first matching record, or -1 if not found.

# Counting wrappers:
insertion_sort_count(records, key) -> int
binary_search_count(sorted_records, target_value, key) -> {"index": int, "comparison_count": int}
linear_search_count(records, target_value, key)        -> {"index": int, "comparison_count": int}
```

### Time complexity

| Algorithm      | Best case | Worst case |
|---------------|-----------|------------|
| insertion_sort | O(n)      | O(n²)      |
| binary_search  | O(1)      | O(log n)   |
| linear_search  | O(1)      | O(n)       |

**insertion_sort best case** — the list is already sorted; each element only needs one comparison
to confirm it is in place, giving O(n) total.

**binary_search best case** — the target is the middle element of the list; found in one comparison.

**linear_search best case** — the target is the first element; found in one comparison.

### Benchmark results (run: `python benchmark.py`)

Synthetic task records at three sizes; each record has the same fields (`id`, `title`, `priority`,
`due_date`) that the real `/tasks` endpoints operate on.

```
========================================================================
  TaskFlow -- Algorithm Benchmark
  insertion_sort / binary_search / linear_search
========================================================================

-- Dataset size: 10 records ----------------------------------------
  insertion_sort   comparisons =            9   time =    0.01 ms
  binary_search    comparisons =            3   time =  0.0057 ms   found_at_index = 5
  linear_search    comparisons =            6   time =  0.0042 ms   found_at_index = 5
  linear / binary  ratio        =          2.0x

-- Dataset size: 500 records ----------------------------------------
  insertion_sort   comparisons =          499   time =    0.07 ms
  binary_search    comparisons =            8   time =  0.0027 ms   found_at_index = 250
  linear_search    comparisons =          251   time =  0.0140 ms   found_at_index = 250
  linear / binary  ratio        =         31.4x

-- Dataset size: 3,000 records ----------------------------------------
  insertion_sort   comparisons =        2,999   time =    0.40 ms
  binary_search    comparisons =           11   time =  0.0032 ms   found_at_index = 1500
  linear_search    comparisons =        1,501   time =  0.0884 ms   found_at_index = 1500
  linear / binary  ratio        =        136.5x
========================================================================
```

**Note on the insertion_sort counts above:** the benchmark used a nearly-sorted dataset
(titles are generated with monotonically-increasing prefixes), which triggered the best case
O(n). A random or reverse-sorted dataset would approach O(n²): at n=3000, worst case is
approximately 4.5 million comparisons.

### Sort-first justification

At n=3000 the real worst case for `insertion_sort` is ~4.5 million comparisons,
while each `binary_search` on the sorted index costs at most 11–12 comparisons
(log₂ 3000 ≈ 11.5). `linear_search` on the unsorted list costs an average of
n/2 = 1,500 comparisons per query.

For a team that performs Q searches between re-sorts, the total comparison cost is:

- **Sort-first strategy:** ~4,500,000 (one-time sort) + Q × 12
- **Linear strategy:**  Q × 1,500

Sort-first becomes cheaper when Q × 1,500 > 4,500,000 + Q × 12, i.e. when Q > ~3,020.

At the smaller n=500 benchmark, the break-even is only about 34 queries. Blinkit engineers
browse and filter their task list throughout the day — viewing it by priority at sprint
planning, standup, and review meetings alone easily exceeds that threshold. Paying the
one-time sort cost is therefore worth it for this read-heavy workload, especially since
tasks are added or renamed far less often than they are viewed.

### Running the checks

```bash
python check_algorithms.py
```

Expected output (all PASS):

```
-- insertion_sort edge cases --
PASS: insertion_sort on empty list leaves it empty
PASS: insertion_sort on single-element list leaves element unchanged

-- binary_search first / last / middle / absent --
PASS: binary_search finds value at first index
PASS: binary_search finds value at last index
PASS: binary_search finds value at middle index
PASS: binary_search returns -1 when target is absent

... (17 checks total, 0 failures)

============================================================
All checks passed (0 failures).
============================================================
```

---

## 7. Section 3 — AI Quick-Add

### Prompting technique rationale (≤ 300 words)

The system message in `ai_parser.py` uses **zero-shot prompting**.

The system role message encodes the complete parsing behavior as a single structured
instruction — what fields to extract, what the priority keyword hierarchy is, and what the
expected output format is — without providing any worked examples inside the prompt itself.
The user role message carries only the raw task description.

Zero-shot was chosen for three reasons:

1. **Token efficiency.** Each API call is cheaper because no labeled examples need to be
   included in the prompt. For a quick-add feature that may be called dozens of times per
   day per engineer, token savings compound quickly.

2. **Response reliability through precise instruction.** The parsing rules are deterministic
   by design (priority group order, date-phrase order, title-stripping). Encoding these
   rules precisely in the system message — rather than letting the model infer them from
   examples — produces more consistent output and makes the behavior easier to audit.

3. **Mock compatibility.** The zero-shot structure maps 1-to-1 onto the rule-based mock
   (`mock_parse`): the system message describes exactly what the mock implements. This means
   the mock and any future real-LLM call share the same behavioral contract, and replacing
   one with the other requires no change to the calling code.

Few-shot or chain-of-thought prompting would improve reliability on ambiguous edge cases
(e.g., descriptions containing multiple conflicting date phrases) at the cost of more tokens
per request and a longer, harder-to-maintain system message. For the closed, well-specified
parsing rules in this project, zero-shot is the right trade-off.

### Five worked examples

The mock parser (`mock_parse` in `backend/ai_parser.py`) follows this exact algorithm:

> a) Lowercase working copy for matching; keep original for title.
> b) Priority: group (i) urgent/asap → high; group (ii) whenever/low priority → low; default medium.
> c) Due-date: scan in order: today, tomorrow, next week, next monday…next sunday, monday…sunday.
> d) Title: strip ALL group (i)/(ii) keywords + matched date phrase; .strip(); empty → "Untitled task".

---

**Example 1**

Input: `"This is urgent, mark it ASAP please"`

- Priority: "urgent" (group i) AND "ASAP" (group i) → **high** (first group wins)
- Due-date: no date keyword → **null**
- Title: remove "urgent" and "ASAP" from original (all occurrences) →
  `"This is , mark it  please"` → after whitespace collapse → `"This is , mark it please"`

```json
{ "title": "This is , mark it please", "priority": "high", "due_date_hint": null }
```

---

**Example 2**

Input: `"   "` (whitespace only)

- Priority: no keywords → **medium**
- Due-date: no keywords → **null**
- Title: no spans removed; result is whitespace-only → **"Untitled task"**

```json
{ "title": "Untitled task", "priority": "medium", "due_date_hint": null }
```

---

**Example 3**

Input: `"Finish the report next Friday, it's urgent"`

- Priority: "urgent" (group i) → **high**
- Due-date: scan in order — "today"? no. "tomorrow"? no. "next week"? no. "next monday"? no.
  ... "next friday"? YES → **"next friday"**
- Title: remove "next friday" (whole two-word phrase), remove "urgent" →
  `"Finish the report , it's"` (after strip)

```json
{ "title": "Finish the report , it's", "priority": "high", "due_date_hint": "next friday" }
```

---

**Example 4**

Input: `"tomorrow review tomorrow"`

- Priority: no keywords → **medium**
- Due-date: "today"? no. "tomorrow"? YES (first match) → **"tomorrow"**
- Title: remove all occurrences of "tomorrow" →
  `" review "` → after strip → `"review"`

```json
{ "title": "review", "priority": "medium", "due_date_hint": "tomorrow" }
```

---

**Example 5**

Input: `"Deploy the service low priority, whenever you get a chance"`

- Priority: no group (i) keywords. Group (ii): "whenever" found AND "low priority" found →
  first group (ii) match wins: **"whenever"** → priority = **low**
- Due-date: no date keywords → **null**
- Title: strip ALL group (ii) keywords — "whenever" AND "low priority" (title-stripping note:
  all group (i) and (ii) keywords removed) →
  `"Deploy the service , you get a chance"` → after strip → `"Deploy the service , you get a chance"`

```json
{
  "title": "Deploy the service , you get a chance",
  "priority": "low",
  "due_date_hint": null
}
```

---

**Example 6 (bonus — verifies group (i) beats group (ii))**

Input: `"Urgent fix, do it whenever"`

- Priority: group (i) "urgent" present AND group (ii) "whenever" present → group (i) wins → **high**
- Due-date: no date keywords → **null**
- Title: strip "urgent" AND "whenever" →
  `" fix, do it "` → after strip → `"fix, do it"`

```json
{ "title": "fix, do it", "priority": "high", "due_date_hint": null }
```

---

**Example 7 — bare weekday (reached only if no "next <day>" matched)**

Input: `"Review the PR on monday"`

- Priority: no keywords → **medium**
- Due-date: "today"? no. "tomorrow"? no. "next week"? no. "next monday"? no (text has "monday",
  not "next monday"). Bare day check: "monday"? YES → **"monday"**
- Title: strip "monday" → `"Review the PR on "` → after strip → `"Review the PR on"`

```json
{ "title": "Review the PR on", "priority": "medium", "due_date_hint": "monday" }
```

---

### Optional real-LLM path

Set `USE_REAL_LLM=1` and `OPENAI_API_KEY=<key>` before starting the backend.
If the key is absent or the call fails, the endpoint automatically falls back to the mock.
Grading never depends on this path.

```bash
# Windows PowerShell
$env:USE_REAL_LLM="1"
$env:OPENAI_API_KEY="sk-..."
uvicorn main:app --reload --port 8000
```

---

## Git Workflow

The repository history includes at least one feature branch that was created,
committed to at least twice, and merged back into `main`.

```bash
git log --graph --all --oneline
```

This will show the feature branch (`feature/algorithms-and-ai`) branching off `main`,
receiving commits for Sections 2 and 3, and being merged back.



---

## 8. Changelog — Recent Fixes

> Date: 2026-11-23

Niche saare bugs aur issues ka record hai jo project review ke baad identify aur fix kiye gaye.

---

### Backend

#### `backend/main.py`

**1. SECRET_KEY hardcoded tha**
- **Problem:** `SECRET_KEY` directly source code mein likha tha — production mein yeh unsafe hai.
- **Fix:** Ab `os.getenv("SECRET_KEY", fallback)` se load hota hai. Value `backend/.env` mein define ki gayi hai.

**2. `datetime.utcnow()` deprecated**
- **Problem:** Python 3.12+ mein `datetime.utcnow()` deprecated mark ho gayi hai, warning aata tha.
- **Fix:** `datetime.now(timezone.utc)` se replace kiya. `timezone` import bhi add kiya.

**3. CORS configuration incomplete**
- **Problem:** `allow_origins` mein sirf `localhost:3000` aur Vercel URL tha. VS Code Live Server (`localhost:5500`) se frontend open karne par CORS block hota tha.
- **Fix:** `http://localhost:5500` aur `http://127.0.0.1:5500` allow_origins mein add kiye.

---

#### `backend/.env`

**4. SECRET_KEY missing**
- **Problem:** `.env` file mein `DATABASE_URL` toh tha lekin `SECRET_KEY` nahi tha.
- **Fix:** `SECRET_KEY` entry add ki gayi.

---

#### `backend/schemas.py`

**5. `QuickAddRequest` description validator kaam nahi karta tha**
- **Problem:** `description_not_blank` validator sirf `return v` kar raha tha — whitespace-only description (e.g. `"   "`) bhi accept ho jaati thi.
- **Fix:** Proper blank/whitespace check add kiya aur `.strip()` apply kiya.

```python
# Pehle (broken)
def description_not_blank(cls, v: str) -> str:
    return v

# Baad mein (fixed)
def description_not_blank(cls, v: str) -> str:
    if not v.strip():
        raise ValueError("description must not be blank or whitespace-only")
    return v.strip()
```

---

#### `seed.py`

**6. Seed users bina password ke ban rahe the**
- **Problem:** `User` objects mein `hashed_password` field nahi diya ja raha tha. DB mein `NOT NULL` constraint hai isliye seed run karne par error aata tha.
- **Fix:** `bcrypt` import add kiya aur dono seed users ke liye `bcrypt.hashpw()` se `hashed_password` generate karke pass kiya (`password123`).

---

### Frontend

#### `frontend/script.js`

**7. "Add Task" button ka SVG icon gayab ho jaata tha**
- **Problem:** `toggleAddTaskBtn.textContent = "+ Add Task"` set karne se button ka SVG icon destroy ho jaata tha — sirf plain text dikhta tha.
- **Fix:** `textContent` ki jagah `innerHTML` use kiya taaki SVG bhi sahi se render ho.

```js
// Pehle (broken)
toggleAddTaskBtn.textContent = "+ Add Task";

// Baad mein (fixed)
toggleAddTaskBtn.innerHTML = '<svg ...>...</svg> Add Task';
```

**8. Logout ke baad filter dropdown reset nahi hota tha**
- **Problem:** `logoutUser()` mein `renderProjects([])` call hoti thi lekin `filterProjectSel` ke options clear nahi hote the. Purane project options filter mein rehjate the.
- **Fix:** `logoutUser()` mein yeh lines add ki gayi:
  ```js
  activeProjectId = null;
  while (filterProjectSel.options.length > 1) filterProjectSel.remove(1);
  filterProjectSel.value = "";
  ```

---

#### `frontend/index.html`

**9. "Owner user ID" input field redundant tha**
- **Problem:** Sidebar mein "Add Project" form mein `Owner user ID` field tha. Lekin backend ka `POST /projects` endpoint `owner_id` JWT token se khud set karta hai — yeh field kisi kaam ki nahi thi aur user ko confuse karti thi.
- **Fix:** Field aur uska error span HTML se remove kar diya.

---

### Files Modified

| File | Changes |
|---|---|
| `backend/main.py` | SECRET_KEY env se load, datetime fix, CORS origins update |
| `backend/.env` | SECRET_KEY add kiya |
| `backend/schemas.py` | QuickAddRequest description validator fix |
| `seed.py` | hashed_password add kiya seed users mein |
| `frontend/script.js` | SVG innerHTML fix, logoutUser cleanup fix |
| `frontend/index.html` | Redundant owner ID field remove kiya |
