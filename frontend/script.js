"use strict";

// -----------------------------------------------------------------
// Config & Constants
// -----------------------------------------------------------------
const API_BASE        = "https://taskflow-fullstack-vrqz.onrender.com";
const LS_TASKS_KEY    = "taskflow_tasks";
const LS_PROJECTS_KEY = "taskflow_projects";
const LS_TOKEN_KEY    = "taskflow_token";

// -----------------------------------------------------------------
// State
// -----------------------------------------------------------------
let tasks    = [];
let projects = [];
let activeProjectId = null;
let authToken = localStorage.getItem(LS_TOKEN_KEY) || null;

// -----------------------------------------------------------------
// DOM refs
// -----------------------------------------------------------------

// User form
const userForm         = document.getElementById("user-form");
const userNameInput    = document.getElementById("user-name-input");
const userEmailInput   = document.getElementById("user-email-input");
const userNameError    = document.getElementById("user-name-error");
const userEmailError   = document.getElementById("user-email-error");

// Project form
const projectForm      = document.getElementById("project-form");
const projectNameInput = document.getElementById("project-name-input");
const projectOwnerInput= document.getElementById("project-owner-input");
const projectNameError = document.getElementById("project-name-error");
const projectOwnerError= document.getElementById("project-owner-error");
const projectListEl    = document.getElementById("project-list");

// Task form
const taskForm         = document.getElementById("task-form");
const taskTitleInput   = document.getElementById("task-title-input");
const taskDescInput    = document.getElementById("task-desc-input");
const taskPriorityInput= document.getElementById("task-priority-input");
const taskDueInput     = document.getElementById("task-due-input");
const taskProjectSelect= document.getElementById("task-project-select");
const taskTitleError   = document.getElementById("task-title-error");
const taskProjectError = document.getElementById("task-project-error");

// Add task toggle
const toggleAddTaskBtn = document.getElementById("toggle-add-task-btn");
const cancelAddTaskBtn = document.getElementById("cancel-add-task-btn");
const addTaskPanel     = document.getElementById("add-task-panel");

// Kanban columns
const todoList         = document.getElementById("task-list-todo");
const inprogressList   = document.getElementById("task-list-inprogress");
const doneList         = document.getElementById("task-list-done");
const emptyTodo        = document.getElementById("empty-todo");
const emptyInprogress  = document.getElementById("empty-inprogress");
const emptyDone        = document.getElementById("empty-done");
const todoCount        = document.getElementById("todo-count");
const inprogressCount  = document.getElementById("inprogress-count");
const doneCount        = document.getElementById("done-count");
const taskCountBadge   = document.getElementById("task-count-badge");

// Search / sort
const searchInput       = document.getElementById("search-input");
const searchAlgoSelect  = document.getElementById("search-algo-select");
const searchBtn         = document.getElementById("search-btn");
const sortSelect        = document.getElementById("sort-select");
const filterProjectSel  = document.getElementById("filter-project-select");
const sortBtn           = document.getElementById("sort-btn");
const clearSearchBtn    = document.getElementById("clear-search-btn");
const searchResultBanner= document.getElementById("search-result-banner");

// Quick-add form
const quickAddForm      = document.getElementById("quick-add-form");
const quickDescInput    = document.getElementById("quick-desc-input");
const quickProjectSelect= document.getElementById("quick-project-select");
const quickDescError    = document.getElementById("quick-desc-error");
const quickProjectError = document.getElementById("quick-project-error");

// Edit modal
const editModal        = document.getElementById("edit-modal");
const editForm         = document.getElementById("edit-form");
const editTaskId       = document.getElementById("edit-task-id");
const editTitle        = document.getElementById("edit-title");
const editDescription  = document.getElementById("edit-description");
const editPriority     = document.getElementById("edit-priority");
const editDue          = document.getElementById("edit-due");
const editStatus       = document.getElementById("edit-status");
const editTitleError   = document.getElementById("edit-title-error");
const modalCancelBtn   = document.getElementById("modal-cancel-btn");

// Toast
const toast = document.getElementById("toast");

// -----------------------------------------------------------------
// Utilities & Auth API Fetch Wrapper
// -----------------------------------------------------------------

function showToast(msg, type = "success") {
  toast.textContent = msg;
  toast.className = `toast ${type}`;
  toast.hidden = false;
  clearTimeout(toast._t);
  toast._t = setTimeout(() => { toast.hidden = true; }, 3000);
}

function setError(el, msg) { el.textContent = msg; }
function clearError(el)    { el.textContent = ""; }

function persistTasksToLS(arr) {
  try { localStorage.setItem(LS_TASKS_KEY, JSON.stringify(arr)); } catch (_) {}
}
function loadTasksFromLS() {
  try { const r = localStorage.getItem(LS_TASKS_KEY); return r ? JSON.parse(r) : []; }
  catch (_) { return []; }
}
function persistProjectsToLS(arr) {
  try { localStorage.setItem(LS_PROJECTS_KEY, JSON.stringify(arr)); } catch (_) {}
}
function loadProjectsFromLS() {
  try { const r = localStorage.getItem(LS_PROJECTS_KEY); return r ? JSON.parse(r) : []; }
  catch (_) { return []; }
}

/** Authenticated Fetch helper that attaches JWT Token */
async function apiFetch(path, options = {}) {
  const headers = { ...options.headers };
  
  if (!(options.body instanceof URLSearchParams)) {
    headers["Content-Type"] = "application/json";
  }

  // 1. JWT token tabhi bhejo jab token ho AUR path login/user creation waala na ho
  if (authToken && path !== "/token" && path !== "/users") {
    headers["Authorization"] = `Bearer ${authToken}`;
  }

  try {
    const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

    // 2. Clear token if expired
    if (res.status === 401 && path !== "/token") {
      localStorage.removeItem(LS_TOKEN_KEY);
      authToken = null;
      showToast("Session expired. Please log in again.", "error");
      throw new Error("Unauthorized");
    }

    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      try { const b = await res.json(); detail = b.detail || JSON.stringify(b); } catch (_) {}
      throw new Error(detail);
    }

    if (res.status === 204) return null;
    return await res.json();

  } catch (err) {
    // 3. Agar Network Error ya CORS ka error ho
    if (err.message === "Failed to fetch") {
      throw new Error("Backend server connect nahi ho raha hai (Server Check Karein)");
    }
    throw err;
  }
}

// -----------------------------------------------------------------
// Toggle Add Task panel
// -----------------------------------------------------------------

toggleAddTaskBtn.addEventListener("click", () => {
  const isOpen = addTaskPanel.classList.contains("add-task-open");
  if (isOpen) {
    addTaskPanel.classList.remove("add-task-open");
    addTaskPanel.classList.add("add-task-collapsed");
    toggleAddTaskBtn.textContent = "+ Add Task";
  } else {
    addTaskPanel.classList.remove("add-task-collapsed");
    addTaskPanel.classList.add("add-task-open");
    toggleAddTaskBtn.textContent = "✕ Close";
    taskTitleInput.focus();
  }
});

cancelAddTaskBtn.addEventListener("click", () => {
  addTaskPanel.classList.remove("add-task-open");
  addTaskPanel.classList.add("add-task-collapsed");
  toggleAddTaskBtn.textContent = "+ Add Task";
  taskForm.reset();
  clearError(taskTitleError);
  clearError(taskProjectError);
});

// -----------------------------------------------------------------
// Rendering helpers
// -----------------------------------------------------------------

function makeChip(text, cls) {
  const s = document.createElement("span");
  s.className = `chip ${cls}`;
  s.textContent = text;
  return s;
}

function buildTaskItem(task) {
  const li = document.createElement("li");
  li.className = `task-item${task.status === "done" ? " done" : ""}`;
  li.dataset.id = String(task.id);

  const cb = document.createElement("input");
  cb.type = "checkbox";
  cb.className = "task-checkbox";
  cb.checked = task.status === "done";
  cb.title = "Toggle done";
  cb.addEventListener("change", () => toggleTaskDone(task, cb, li));
  li.appendChild(cb);

  const content = document.createElement("div");
  content.className = "task-content";

  const titleEl = document.createElement("span");
  titleEl.className = "task-title";
  titleEl.textContent = task.title;
  content.appendChild(titleEl);

  if (task.description) {
    const desc = document.createElement("p");
    desc.className = "task-desc-text";
    desc.textContent = task.description;
    content.appendChild(desc);
  }

  const meta = document.createElement("div");
  meta.className = "task-meta";
  meta.appendChild(makeChip(task.priority, `chip-priority-${task.priority}`));
  if (task.due_date) {
    const due = document.createElement("span");
    due.className = "task-due";
    due.textContent = `📅 ${task.due_date}`;
    meta.appendChild(due);
  }
  content.appendChild(meta);
  li.appendChild(content);

  const actions = document.createElement("div");
  actions.className = "task-actions";

  const editBtn = document.createElement("button");
  editBtn.className = "btn-edit";
  editBtn.textContent = "Edit";
  editBtn.type = "button";
  editBtn.addEventListener("click", () => openEditModal(task));

  const delBtn = document.createElement("button");
  delBtn.className = "btn-danger";
  delBtn.textContent = "Del";
  delBtn.type = "button";
  delBtn.addEventListener("click", () => deleteTask(task.id));

  actions.appendChild(editBtn);
  actions.appendChild(delBtn);
  li.appendChild(actions);

  return li;
}

function renderTasks(taskArray) {
  [todoList, inprogressList, doneList].forEach(ul => {
    while (ul.firstChild) ul.removeChild(ul.firstChild);
  });

  let nTodo = 0, nProg = 0, nDone = 0;

  taskArray.forEach(task => {
    const li = buildTaskItem(task);
    if (task.status === "done") {
      doneList.appendChild(li);
      nDone++;
    } else if (task.status === "in_progress") {
      inprogressList.appendChild(li);
      nProg++;
    } else {
      todoList.appendChild(li);
      nTodo++;
    }
  });

  todoCount.textContent       = String(nTodo);
  inprogressCount.textContent = String(nProg);
  doneCount.textContent       = String(nDone);
  taskCountBadge.textContent  = String(taskArray.length);

  emptyTodo.style.display       = nTodo === 0 ? "block" : "none";
  emptyInprogress.style.display = nProg === 0 ? "block" : "none";
  emptyDone.style.display       = nDone === 0 ? "block" : "none";

  persistTasksToLS(taskArray);
}

// -----------------------------------------------------------------
// Task Operations
// -----------------------------------------------------------------

async function toggleTaskDone(task, cb, li) {
  const newStatus = cb.checked ? "done" : "todo";
  try {
    const updated = await apiFetch(`/tasks/${task.id}`, {
      method: "PUT",
      body: JSON.stringify({ status: newStatus }),
    });
    const idx = tasks.findIndex(t => t.id === task.id);
    if (idx !== -1) tasks[idx] = updated;
    renderTasks(tasks);
    showToast(newStatus === "done" ? "Marked as done!" : "Task reopened.");
  } catch (err) {
    cb.checked = !cb.checked;
    showToast(`Failed: ${err.message}`, "error");
  }
}

function renderProjects(projectArray) {
  [taskProjectSelect, quickProjectSelect, filterProjectSel].forEach(sel => {
    const prev = sel.value;
    while (sel.options.length > 1) sel.remove(1);
    projectArray.forEach(p => {
      const opt = document.createElement("option");
      opt.value = String(p.id);
      opt.textContent = p.name;
      sel.appendChild(opt);
    });
    if (prev) sel.value = prev;
  });

  while (projectListEl.firstChild) projectListEl.removeChild(projectListEl.firstChild);

  const allItem = document.createElement("div");
  allItem.className = `project-item${activeProjectId === null ? " active" : ""}`;
  const allName = document.createElement("span");
  allName.className = "project-item-name";
  allName.textContent = "📋 All projects";
  allName.addEventListener("click", () => selectProject(null));
  allItem.appendChild(allName);
  projectListEl.appendChild(allItem);

  projectArray.forEach(p => {
    const item = document.createElement("div");
    item.className = `project-item${activeProjectId === p.id ? " active" : ""}`;

    const nameSpan = document.createElement("span");
    nameSpan.className = "project-item-name";
    nameSpan.textContent = p.name;
    nameSpan.addEventListener("click", () => selectProject(p.id));
    item.appendChild(nameSpan);

    const delBtn = document.createElement("button");
    delBtn.className = "btn-delete-project";
    delBtn.title = "Delete project";
    delBtn.textContent = "🗑";
    delBtn.type = "button";
    delBtn.addEventListener("click", e => { e.stopPropagation(); deleteProject(p.id, p.name); });
    item.appendChild(delBtn);

    projectListEl.appendChild(item);
  });

  persistProjectsToLS(projectArray);
}

// -----------------------------------------------------------------
// Data Loading
// -----------------------------------------------------------------

async function loadTasks(projectId = null) {
  try {
    const url = projectId ? `/tasks?project_id=${projectId}` : "/tasks";
    const data = await apiFetch(url);
    tasks = data;
    renderTasks(tasks);
  } catch (err) {
    // Agar server se data nahi mila, toh LocalStorage se load karo
    const cachedTasks = loadTasksFromLS();
    if (cachedTasks && cachedTasks.length > 0) {
      tasks = cachedTasks;
      renderTasks(tasks);
      showToast("Offline mode: Saved data loaded", "error");
    } else {
      showToast(`Tasks load nahi ho paye: ${err.message}`, "error");
    }
  }
}

async function loadProjects() {
  try {
    const data = await apiFetch("/projects");
    projects = data;
    renderProjects(projects);
  } catch (err) {
    if (err.message !== "Unauthorized") {
      showToast(`Could not load projects: ${err.message}`, "error");
    }
  }
}

async function selectProject(projectId) {
  activeProjectId = projectId;
  renderProjects(projects);
  await loadTasks(projectId);
}

// -----------------------------------------------------------------
// User & Auth Login Flow
// -----------------------------------------------------------------

userForm.addEventListener("submit", async e => {
  e.preventDefault();
  let ok = true;
  const name  = userNameInput.value.trim();
  const email = userEmailInput.value.trim();
  if (!name)  { setError(userNameError,  "Name required."); ok = false; } else clearError(userNameError);
  if (!email || !email.includes("@")) { setError(userEmailError, "Valid email required."); ok = false; } else clearError(userEmailError);
  if (!ok) return;

  try {
    // 1. Create User
    await apiFetch("/users", { 
      method: "POST", 
      body: JSON.stringify({ name, email, password: "password123" }) 
    });

    // 2. Auto Login to acquire JWT Token
    const formData = new URLSearchParams();
    formData.append("username", email);
    formData.append("password", "password123");

    const tokenRes = await apiFetch("/token", {
      method: "POST",
      body: formData,
    });

    authToken = tokenRes.access_token;
    localStorage.setItem(LS_TOKEN_KEY, authToken);

    userForm.reset();
    showToast(`Logged in as "${name}"!`);
    await init();
  } catch (err) { 
    showToast(`Auth error: ${err.message}`, "error"); 
  }
});

// -----------------------------------------------------------------
// Add Project
// -----------------------------------------------------------------

projectForm.addEventListener("submit", async e => {
  e.preventDefault();
  let ok = true;
  const name = projectNameInput.value.trim();
  if (!name) { setError(projectNameError, "Name required."); ok = false; } else clearError(projectNameError);
  if (!ok) return;

  try {
    const p = await apiFetch("/projects", { method: "POST", body: JSON.stringify({ name }) });
    projects.push(p);
    renderProjects(projects);
    projectForm.reset();
    showToast(`Project "${p.name}" created!`);
  } catch (err) { showToast(`Project error: ${err.message}`, "error"); }
});

async function deleteProject(id, name) {
  // 1. User se confirm karo
  if (!confirm(`Delete project "${name}"?`)) return;

  try {
    // 2. Server se delete karo
    await apiFetch(`/projects/${id}`, { method: "DELETE" });

    // 3. Local list se hatao
    projects = projects.filter(p => p.id !== id);

    // 4. Reset karo agar wahi project active tha
    if (activeProjectId === id) {
      activeProjectId = null;
    }

    // 5. Screen update karo
    renderProjects(projects);
    loadTasks(null);
    showToast("Project deleted!");

  } catch (err) {
    showToast("Delete nahi ho paya", "error");
  }
}

// -----------------------------------------------------------------
// Add Task
// -----------------------------------------------------------------

taskForm.addEventListener("submit", async e => {
  e.preventDefault();
  let ok = true;
  const title = taskTitleInput.value.trim();
  const projectId = taskProjectSelect.value;
  if (!title)     { setError(taskTitleError,   "Title required."); ok = false; } else clearError(taskTitleError);
  if (!projectId) { setError(taskProjectError, "Select a project."); ok = false; } else clearError(taskProjectError);
  if (!ok) return;

  try {
    const newTask = await apiFetch("/tasks", {
      method: "POST",
      body: JSON.stringify({
        title,
        description: taskDescInput.value.trim() || null,
        priority: taskPriorityInput.value,
        due_date: taskDueInput.value.trim() || null,
        status: "todo",
        project_id: parseInt(projectId, 10),
      }),
    });
    tasks.unshift(newTask);
    renderTasks(tasks);
    taskForm.reset();
    addTaskPanel.classList.remove("add-task-open");
    addTaskPanel.classList.add("add-task-collapsed");
    toggleAddTaskBtn.textContent = "+ Add Task";
    showToast("Task added!");
  } catch (err) { showToast(`Error: ${err.message}`, "error"); }
});

taskTitleInput.addEventListener("input", () => { if (taskTitleInput.value.trim()) clearError(taskTitleError); });

// -----------------------------------------------------------------
// AI Quick-Add
// -----------------------------------------------------------------

quickAddForm.addEventListener("submit", async e => {
  e.preventDefault();
  let ok = true;
  const desc = quickDescInput.value;
  const projectId = quickProjectSelect.value;
  if (!desc || !desc.trim()) { setError(quickDescError,    "Enter a description."); ok = false; } else clearError(quickDescError);
  if (!projectId)            { setError(quickProjectError, "Select a project.");    ok = false; } else clearError(quickProjectError);
  if (!ok) return;

  const btn = quickAddForm.querySelector("button[type=submit]");
  const orig = btn.textContent;
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span>Parsing…';

  try {
    const newTask = await apiFetch("/tasks/quick-add", {
      method: "POST",
      body: JSON.stringify({ description: desc, project_id: parseInt(projectId, 10) }),
    });
    tasks.unshift(newTask);
    renderTasks(tasks);
    quickAddForm.reset();
    showToast(`Created: "${newTask.title}" (${newTask.priority})`);
  } catch (err) {
    showToast(`Quick-Add error: ${err.message}`, "error");
  } finally {
    btn.disabled = false;
    btn.textContent = orig;
  }
});

// -----------------------------------------------------------------
// Edit Modal
// -----------------------------------------------------------------

function openEditModal(task) {
  editTaskId.value       = String(task.id);
  editTitle.value        = task.title;
  editDescription.value  = task.description || "";
  editPriority.value     = task.priority;
  editDue.value          = task.due_date || "";
  editStatus.value       = task.status;
  clearError(editTitleError);
  editModal.hidden = false;
  editTitle.focus();
}
function closeEditModal() { editModal.hidden = true; }

modalCancelBtn.addEventListener("click", closeEditModal);
editModal.addEventListener("click", e => { if (e.target === editModal) closeEditModal(); });
document.addEventListener("keydown", e => { if (e.key === "Escape" && !editModal.hidden) closeEditModal(); });

editForm.addEventListener("submit", async e => {
  e.preventDefault();
  const title = editTitle.value.trim();
  if (!title) { setError(editTitleError, "Title required."); return; }
  clearError(editTitleError);

  const id = parseInt(editTaskId.value, 10);
  try {
    const updated = await apiFetch(`/tasks/${id}`, {
      method: "PUT",
      body: JSON.stringify({
        title,
        description: editDescription.value.trim() || null,
        priority:    editPriority.value,
        due_date:    editDue.value.trim() || null,
        status:      editStatus.value,
      }),
    });
    const idx = tasks.findIndex(t => t.id === id);
    if (idx !== -1) tasks[idx] = updated;
    renderTasks(tasks);
    closeEditModal();
    showToast("Task updated.");
  } catch (err) { showToast(`Update failed: ${err.message}`, "error"); }
});

// -----------------------------------------------------------------
// Delete Task
// -----------------------------------------------------------------

async function deleteTask(id) {
  if (!confirm("Delete this task?")) return;
  try {
    await apiFetch(`/tasks/${id}`, { method: "DELETE" });
    tasks = tasks.filter(t => t.id !== id);
    renderTasks(tasks);
    showToast("Task deleted.");
  } catch (err) { showToast(`Delete failed: ${err.message}`, "error"); }
}

// -----------------------------------------------------------------
// Search & Sort
// -----------------------------------------------------------------

searchBtn.addEventListener("click", async () => {
  const title = searchInput.value.trim();
  if (!title) { showToast("Enter a title to search.", "error"); return; }
  const algo = searchAlgoSelect.value;
  try {
    const found = await apiFetch(`/tasks/search?title=${encodeURIComponent(title)}&algo=${algo}`);
    searchResultBanner.className = "search-banner";
    searchResultBanner.textContent = `Found: "${found.title}" (ID ${found.id}) — ${algo} search`;

    document.querySelectorAll(".task-item.highlight").forEach(el => el.classList.remove("highlight"));
    const match = document.querySelector(`.task-item[data-id="${found.id}"]`);
    if (match) { match.classList.add("highlight"); match.scrollIntoView({ behavior: "smooth", block: "nearest" }); }
  } catch (err) {
    searchResultBanner.className = "search-banner error";
    searchResultBanner.textContent = `Not found: ${err.message}`;
  }
});

searchInput.addEventListener("keydown", e => { if (e.key === "Enter") searchBtn.click(); });

sortBtn.addEventListener("click", async () => {
  const sortBy    = sortSelect.value;
  const projectId = filterProjectSel.value || null;
  if (!sortBy) { showToast("Pick a sort field.", "error"); return; }
  try {
    let qs = `?sort=${sortBy}`;
    if (projectId) qs += `&project_id=${projectId}`;
    const sorted = await apiFetch(`/tasks${qs}`);
    tasks = sorted;
    renderTasks(tasks);
    showToast(`Sorted by ${sortBy}`);
  } catch (err) { showToast(`Sort failed: ${err.message}`, "error"); }
});

clearSearchBtn.addEventListener("click", async () => {
  searchInput.value = "";
  searchResultBanner.textContent = "";
  searchResultBanner.className = "search-banner";
  document.querySelectorAll(".task-item.highlight").forEach(el => el.classList.remove("highlight"));
  await loadTasks(activeProjectId);
});

// -----------------------------------------------------------------
// Init
// -----------------------------------------------------------------

async function init() {
  if (!authToken) {
    showToast("Please register or log in first.", "error");
    return;
  }
  await loadProjects();
  await loadTasks();
}

init();
function logoutUser() {
  // 1. LocalStorage se token aur data hatao
  localStorage.removeItem(LS_TOKEN_KEY);
  authToken = null;

  // 2. Local lists khali karo
  tasks = [];
  projects = [];

  // 3. Screen update karo
  renderTasks([]);
  renderProjects([]);
  showToast("Logged out successfully!");
}