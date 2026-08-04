/**
 * script.js — TaskFlow Dashboard
 *
 * Features
 * --------
 * - Fetches tasks/projects/users from the real FastAPI backend on page load.
 * - Renders tasks with document.createElement() + appendChild() (no innerHTML
 *   for user-provided values — textContent used for all user data).
 * - Add / Edit / Delete tasks via Fetch API → backend CRUD endpoints.
 * - AI Quick-Add via POST /tasks/quick-add.
 * - Sort and search via the Section 2 backend endpoints.
 * - Client-side validation: empty title → visible error, no submission.
 * - localStorage cache: rendered from cache first while backend request is in flight.
 * - All interactive controls use addEventListener (no inline onclick).
 */

"use strict";

// ─────────────────────────────────────────────────────────────────
// Configuration
// ─────────────────────────────────────────────────────────────────

const API_BASE = "http://127.0.0.1:8000";
const LS_TASKS_KEY    = "taskflow_tasks";
const LS_PROJECTS_KEY = "taskflow_projects";

// ─────────────────────────────────────────────────────────────────
// State
// ─────────────────────────────────────────────────────────────────

let tasks    = [];    // current task list (may be sorted/filtered)
let projects = [];    // all projects
let activeProjectId = null;  // null = show all tasks

// ─────────────────────────────────────────────────────────────────
// DOM references
// ─────────────────────────────────────────────────────────────────

const taskList          = document.getElementById("task-list");
const emptyState        = document.getElementById("empty-state");
const taskCountBadge    = document.getElementById("task-count-badge");
const projectListEl     = document.getElementById("project-list");

// Task form
const taskForm          = document.getElementById("task-form");
const taskTitleInput    = document.getElementById("task-title-input");
const taskDescInput     = document.getElementById("task-desc-input");
const taskPriorityInput = document.getElementById("task-priority-input");
const taskDueInput      = document.getElementById("task-due-input");
const taskProjectSelect = document.getElementById("task-project-select");
const taskTitleError    = document.getElementById("task-title-error");
const taskProjectError  = document.getElementById("task-project-error");

// Quick-add form
const quickAddForm      = document.getElementById("quick-add-form");
const quickDescInput    = document.getElementById("quick-desc-input");
const quickProjectSelect= document.getElementById("quick-project-select");
const quickDescError    = document.getElementById("quick-desc-error");
const quickProjectError = document.getElementById("quick-project-error");

// Search / sort controls
const searchInput       = document.getElementById("search-input");
const searchAlgoSelect  = document.getElementById("search-algo-select");
const searchBtn         = document.getElementById("search-btn");
const sortSelect        = document.getElementById("sort-select");
const sortBtn           = document.getElementById("sort-btn");
const clearSearchBtn    = document.getElementById("clear-search-btn");
const searchResultBanner= document.getElementById("search-result-banner");

// Edit modal
const editModal         = document.getElementById("edit-modal");
const editForm          = document.getElementById("edit-form");
const editTaskId        = document.getElementById("edit-task-id");
const editTitle         = document.getElementById("edit-title");
const editDescription   = document.getElementById("edit-description");
const editPriority      = document.getElementById("edit-priority");
const editDue           = document.getElementById("edit-due");
const editStatus        = document.getElementById("edit-status");
const editTitleError    = document.getElementById("edit-title-error");
const modalCancelBtn    = document.getElementById("modal-cancel-btn");

// User form
const userForm          = document.getElementById("user-form");
const userNameInput     = document.getElementById("user-name-input");
const userEmailInput    = document.getElementById("user-email-input");
const userNameError     = document.getElementById("user-name-error");
const userEmailError    = document.getElementById("user-email-error");

// Project form
const projectForm       = document.getElementById("project-form");
const projectNameInput  = document.getElementById("project-name-input");
const projectOwnerInput = document.getElementById("project-owner-input");
const projectNameError  = document.getElementById("project-name-error");
const projectOwnerError = document.getElementById("project-owner-error");

// Toast
const toast             = document.getElementById("toast");

// ─────────────────────────────────────────────────────────────────
// Utility helpers
// ─────────────────────────────────────────────────────────────────

/** Show a transient toast message. */
function showToast(message, type = "success") {
  toast.textContent = message;
  toast.className = `toast ${type}`;
  toast.hidden = false;
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => { toast.hidden = true; }, 3000);
}

/** Set or clear an inline error message. */
function setError(el, msg) {
  el.textContent = msg;
}
function clearError(el) {
  el.textContent = "";
}

/** Serialise tasks to localStorage. */
function persistTasksToLS(taskArray) {
  try {
    localStorage.setItem(LS_TASKS_KEY, JSON.stringify(taskArray));
  } catch (_) { /* quota errors are non-fatal */ }
}

/** Load tasks from localStorage (may be empty / null). */
function loadTasksFromLS() {
  try {
    const raw = localStorage.getItem(LS_TASKS_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch (_) {
    return [];
  }
}

/** Persist projects to localStorage. */
function persistProjectsToLS(projectArray) {
  try {
    localStorage.setItem(LS_PROJECTS_KEY, JSON.stringify(projectArray));
  } catch (_) {}
}

/** Load projects from localStorage. */
function loadProjectsFromLS() {
  try {
    const raw = localStorage.getItem(LS_PROJECTS_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch (_) {
    return [];
  }
}

/** Generic API fetch wrapper. Throws on non-ok responses. */
async function apiFetch(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch (_) {}
    throw new Error(detail);
  }
  // 204 No Content — nothing to parse
  if (res.status === 204) return null;
  return res.json();
}

// ─────────────────────────────────────────────────────────────────
// Rendering
// ─────────────────────────────────────────────────────────────────

/** Build a chip element. Never uses innerHTML for user values. */
function makeChip(text, className) {
  const span = document.createElement("span");
  span.className = `chip ${className}`;
  span.textContent = text;           // ← textContent, not innerHTML
  return span;
}

/**
 * Render the task list into the DOM.
 * Uses document.createElement + appendChild for every task item.
 * Never builds HTML strings from user input.
 */
function renderTasks(taskArray) {
  // Clear existing items
  while (taskList.firstChild) {
    taskList.removeChild(taskList.firstChild);
  }

  taskCountBadge.textContent = String(taskArray.length);
  emptyState.style.display = taskArray.length === 0 ? "block" : "none";

  taskArray.forEach((task) => {
    const li = document.createElement("li");
    li.className = `task-item${task.status === "done" ? " done" : ""}`;
    li.dataset.id = String(task.id);

    // ── Checkbox (toggles done status) ─────────────────────────
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.className = "task-checkbox";
    checkbox.checked = task.status === "done";
    checkbox.title = "Mark as done";
    checkbox.addEventListener("change", () => toggleTaskDone(task, checkbox, li));
    li.appendChild(checkbox);

    // Content wrapper
    const content = document.createElement("div");
    content.className = "task-content";

    // Title — textContent for user-provided text
    const titleEl = document.createElement("span");
    titleEl.className = "task-title";
    titleEl.textContent = task.title;   // ← textContent (safe DOM update)
    content.appendChild(titleEl);

    // Description below title (if present)
    if (task.description) {
      const descEl = document.createElement("p");
      descEl.className = "task-desc-text";
      descEl.textContent = task.description;  // textContent
      content.appendChild(descEl);
    }

    // Meta row
    const meta = document.createElement("div");
    meta.className = "task-meta";

    meta.appendChild(makeChip(task.priority, `chip-priority-${task.priority}`));
    meta.appendChild(makeChip(
      task.status.replace("_", " "),
      `chip-status-${task.status}`
    ));

    if (task.due_date) {
      const due = document.createElement("span");
      due.className = "task-due";
      due.textContent = `📅 ${task.due_date}`;  // textContent
      meta.appendChild(due);
    }

    content.appendChild(meta);
    li.appendChild(content);

    // Action buttons
    const actions = document.createElement("div");
    actions.className = "task-actions";

    const editBtn = document.createElement("button");
    editBtn.className = "btn btn-edit";
    editBtn.textContent = "Edit";
    editBtn.type = "button";
    editBtn.addEventListener("click", () => openEditModal(task));  // addEventListener

    const deleteBtn = document.createElement("button");
    deleteBtn.className = "btn btn-danger";
    deleteBtn.textContent = "Delete";
    deleteBtn.type = "button";
    deleteBtn.addEventListener("click", () => deleteTask(task.id)); // addEventListener

    actions.appendChild(editBtn);
    actions.appendChild(deleteBtn);
    li.appendChild(actions);

    taskList.appendChild(li);
  });

  // Persist to localStorage every time the list changes
  persistTasksToLS(taskArray);
}

/** Toggle a task's done status via checkbox click. */
async function toggleTaskDone(task, checkbox, li) {
  const newStatus = checkbox.checked ? "done" : "todo";
  try {
    const updated = await apiFetch(`/tasks/${task.id}`, {
      method: "PUT",
      body: JSON.stringify({ status: newStatus }),
    });
    const idx = tasks.findIndex((t) => t.id === task.id);
    if (idx !== -1) tasks[idx] = updated;
    li.classList.toggle("done", newStatus === "done");
    persistTasksToLS(tasks);
    showToast(newStatus === "done" ? "Task marked as done!" : "Task reopened.");
  } catch (err) {
    checkbox.checked = !checkbox.checked; // revert on failure
    showToast(`Update failed: ${err.message}`, "error");
  }
}

/** Populate project dropdowns and sidebar project list. */
function renderProjects(projectArray) {
  // Update selects
  [taskProjectSelect, quickProjectSelect].forEach((sel) => {
    const prev = sel.value;
    while (sel.options.length > 1) sel.remove(1);
    projectArray.forEach((p) => {
      const opt = document.createElement("option");
      opt.value = String(p.id);
      opt.textContent = p.name;          // textContent
      sel.appendChild(opt);
    });
    if (prev) sel.value = prev;
  });

  // Sidebar project list
  while (projectListEl.firstChild) {
    projectListEl.removeChild(projectListEl.firstChild);
  }

  // "All tasks" item
  const allItem = document.createElement("div");
  allItem.className = `project-item${activeProjectId === null ? " active" : ""}`;
  allItem.textContent = "📋 All tasks";
  allItem.addEventListener("click", () => selectProject(null));
  projectListEl.appendChild(allItem);

  projectArray.forEach((p) => {
    const item = document.createElement("div");
    item.className = `project-item${activeProjectId === p.id ? " active" : ""}`;
    item.textContent = p.name;             // textContent
    item.addEventListener("click", () => selectProject(p.id));
    projectListEl.appendChild(item);
  });

  persistProjectsToLS(projectArray);
}

// ─────────────────────────────────────────────────────────────────
// Data loading
// ─────────────────────────────────────────────────────────────────

/** Load tasks from backend; render from LS cache first. */
async function loadTasks(projectId = null) {
  // 1. Render from localStorage immediately (cache-first)
  const cached = loadTasksFromLS();
  if (cached.length > 0) renderTasks(cached);

  // 2. Fetch live data from backend
  try {
    const qs = projectId ? `?project_id=${projectId}` : "";
    const data = await apiFetch(`/tasks${qs}`);
    tasks = data;
    renderTasks(tasks);
  } catch (err) {
    showToast(`Could not load tasks: ${err.message}`, "error");
  }
}

async function loadProjects() {
  // Cache-first
  const cached = loadProjectsFromLS();
  if (cached.length > 0) {
    projects = cached;
    renderProjects(projects);
  }

  try {
    const data = await apiFetch("/projects");
    projects = data;
    renderProjects(projects);
  } catch (err) {
    showToast(`Could not load projects: ${err.message}`, "error");
  }
}

async function selectProject(projectId) {
  activeProjectId = projectId;
  renderProjects(projects);   // re-render sidebar to update active state
  await loadTasks(projectId);
}

// ─────────────────────────────────────────────────────────────────
// Add Task
// ─────────────────────────────────────────────────────────────────

taskForm.addEventListener("submit", async (e) => {
  e.preventDefault();   // ← intercept form submit (required)

  let valid = true;

  const title = taskTitleInput.value.trim();
  if (!title) {
    setError(taskTitleError, "Title is required.");   // ← visible error message
    valid = false;
  } else {
    clearError(taskTitleError);
  }

  const projectId = taskProjectSelect.value;
  if (!projectId) {
    setError(taskProjectError, "Please select a project.");
    valid = false;
  } else {
    clearError(taskProjectError);
  }

  if (!valid) return;  // do not submit if invalid

  const body = {
    title,
    description: taskDescInput.value.trim() || null,
    priority: taskPriorityInput.value,
    due_date: taskDueInput.value.trim() || null,
    status: "todo",
    project_id: parseInt(projectId, 10),
  };

  try {
    const newTask = await apiFetch("/tasks", {
      method: "POST",
      body: JSON.stringify(body),
    });
    tasks.unshift(newTask);
    renderTasks(tasks);
    taskForm.reset();
    showToast("Task added successfully!");
  } catch (err) {
    showToast(`Error: ${err.message}`, "error");
  }
});

// Clear title error as user types
taskTitleInput.addEventListener("input", () => {
  if (taskTitleInput.value.trim()) clearError(taskTitleError);
});

// ─────────────────────────────────────────────────────────────────
// Quick-Add (AI)
// ─────────────────────────────────────────────────────────────────

quickAddForm.addEventListener("submit", async (e) => {
  e.preventDefault();

  let valid = true;

  const desc = quickDescInput.value;
  if (!desc || !desc.trim()) {
    setError(quickDescError, "Please enter a description.");
    valid = false;
  } else {
    clearError(quickDescError);
  }

  const projectId = quickProjectSelect.value;
  if (!projectId) {
    setError(quickProjectError, "Please select a project.");
    valid = false;
  } else {
    clearError(quickProjectError);
  }

  if (!valid) return;

  const submitBtn = quickAddForm.querySelector("button[type=submit]");
  const originalText = submitBtn.textContent;
  submitBtn.disabled = true;
  submitBtn.innerHTML = '<span class="spinner"></span>Parsing…';

  try {
    const newTask = await apiFetch("/tasks/quick-add", {
      method: "POST",
      body: JSON.stringify({
        description: desc,
        project_id: parseInt(projectId, 10),
      }),
    });
    tasks.unshift(newTask);
    renderTasks(tasks);
    quickAddForm.reset();
    // Highlight new task briefly
    const newLi = taskList.querySelector(`[data-id="${newTask.id}"]`);
    if (newLi) {
      newLi.classList.add("highlight");
      setTimeout(() => newLi.classList.remove("highlight"), 2500);
    }
    showToast(`Task created: "${newTask.title}" (${newTask.priority})`);
  } catch (err) {
    showToast(`Quick-Add error: ${err.message}`, "error");
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = originalText;
  }
});

// ─────────────────────────────────────────────────────────────────
// Edit Task modal
// ─────────────────────────────────────────────────────────────────

function openEditModal(task) {
  editTaskId.value = String(task.id);
  editTitle.value  = task.title;
  editDescription.value = task.description || "";
  editPriority.value = task.priority;
  editDue.value    = task.due_date || "";
  editStatus.value = task.status;
  clearError(editTitleError);
  editModal.hidden = false;
  editTitle.focus();
}

function closeEditModal() {
  editModal.hidden = true;
}

modalCancelBtn.addEventListener("click", closeEditModal);

// Close modal on overlay click
editModal.addEventListener("click", (e) => {
  if (e.target === editModal) closeEditModal();
});

// Close modal on Escape key
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !editModal.hidden) closeEditModal();
});

editForm.addEventListener("submit", async (e) => {
  e.preventDefault();

  const title = editTitle.value.trim();
  if (!title) {
    setError(editTitleError, "Title is required.");
    return;
  }
  clearError(editTitleError);

  const id = parseInt(editTaskId.value, 10);
  const body = {
    title,
    description: editDescription.value.trim() || null,
    priority: editPriority.value,
    due_date: editDue.value.trim() || null,
    status: editStatus.value,
  };

  try {
    const updated = await apiFetch(`/tasks/${id}`, {
      method: "PUT",
      body: JSON.stringify(body),
    });
    // Update local state
    const idx = tasks.findIndex((t) => t.id === id);
    if (idx !== -1) tasks[idx] = updated;
    renderTasks(tasks);
    closeEditModal();
    showToast("Task updated.");
  } catch (err) {
    showToast(`Update failed: ${err.message}`, "error");
  }
});

// ─────────────────────────────────────────────────────────────────
// Delete Task
// ─────────────────────────────────────────────────────────────────

async function deleteTask(id) {
  if (!confirm("Delete this task?")) return;
  try {
    await apiFetch(`/tasks/${id}`, { method: "DELETE" });
    tasks = tasks.filter((t) => t.id !== id);
    renderTasks(tasks);
    showToast("Task deleted.");
  } catch (err) {
    showToast(`Delete failed: ${err.message}`, "error");
  }
}

// ─────────────────────────────────────────────────────────────────
// Sort
// ─────────────────────────────────────────────────────────────────

sortBtn.addEventListener("click", async () => {
  const sortBy = sortSelect.value;
  if (!sortBy) { showToast("Pick a sort field first.", "error"); return; }

  try {
    const qs = activeProjectId
      ? `?sort=${sortBy}&project_id=${activeProjectId}`
      : `?sort=${sortBy}`;
    const sorted = await apiFetch(`/tasks${qs}`);
    tasks = sorted;
    renderTasks(tasks);
    showToast(`Sorted by ${sortBy} (insertion sort)`);
  } catch (err) {
    showToast(`Sort failed: ${err.message}`, "error");
  }
});

// ─────────────────────────────────────────────────────────────────
// Search
// ─────────────────────────────────────────────────────────────────

searchBtn.addEventListener("click", async () => {
  const title = searchInput.value.trim();
  if (!title) { showToast("Enter a title to search.", "error"); return; }

  const algo = searchAlgoSelect.value;

  try {
    const found = await apiFetch(
      `/tasks/search?title=${encodeURIComponent(title)}&algo=${algo}`
    );
    searchResultBanner.className = "search-banner";
    searchResultBanner.textContent =
      `Found: "${found.title}" (ID ${found.id}) — ${algo} search`;

    // Highlight matching task if visible in list
    document.querySelectorAll(".task-item.highlight").forEach((el) =>
      el.classList.remove("highlight")
    );
    const match = taskList.querySelector(`[data-id="${found.id}"]`);
    if (match) {
      match.classList.add("highlight");
      match.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  } catch (err) {
    searchResultBanner.className = "search-banner error";
    searchResultBanner.textContent = `Not found: ${err.message}`;
  }
});

clearSearchBtn.addEventListener("click", async () => {
  searchInput.value = "";
  searchResultBanner.textContent = "";
  searchResultBanner.className = "search-banner";
  document.querySelectorAll(".task-item.highlight").forEach((el) =>
    el.classList.remove("highlight")
  );
  await loadTasks(activeProjectId);
});

// Allow pressing Enter in search box
searchInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") searchBtn.click();
});

// ─────────────────────────────────────────────────────────────────
// Add User
// ─────────────────────────────────────────────────────────────────

userForm.addEventListener("submit", async (e) => {
  e.preventDefault();

  let valid = true;
  const name = userNameInput.value.trim();
  const email = userEmailInput.value.trim();

  if (!name) { setError(userNameError, "Name is required."); valid = false; }
  else clearError(userNameError);

  if (!email || !email.includes("@")) {
    setError(userEmailError, "Valid email required.");
    valid = false;
  } else {
    clearError(userEmailError);
  }

  if (!valid) return;

  try {
    await apiFetch("/users", {
      method: "POST",
      body: JSON.stringify({ name, email }),
    });
    userForm.reset();
    showToast(`User "${name}" created!`);
  } catch (err) {
    showToast(`User error: ${err.message}`, "error");
  }
});

// ─────────────────────────────────────────────────────────────────
// Add Project
// ─────────────────────────────────────────────────────────────────

projectForm.addEventListener("submit", async (e) => {
  e.preventDefault();

  let valid = true;
  const name    = projectNameInput.value.trim();
  const ownerId = parseInt(projectOwnerInput.value, 10);

  if (!name) { setError(projectNameError, "Project name required."); valid = false; }
  else clearError(projectNameError);

  if (!ownerId || isNaN(ownerId)) {
    setError(projectOwnerError, "Valid user ID required.");
    valid = false;
  } else {
    clearError(projectOwnerError);
  }

  if (!valid) return;

  try {
    const newProject = await apiFetch("/projects", {
      method: "POST",
      body: JSON.stringify({ name, owner_id: ownerId }),
    });
    projects.push(newProject);
    renderProjects(projects);
    projectForm.reset();
    showToast(`Project "${newProject.name}" created!`);
  } catch (err) {
    showToast(`Project error: ${err.message}`, "error");
  }
});

// ─────────────────────────────────────────────────────────────────
// Initialisation
// ─────────────────────────────────────────────────────────────────

async function init() {
  await loadProjects();
  await loadTasks();
}

// Start the app
init();
