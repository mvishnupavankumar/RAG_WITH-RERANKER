const state = {
  notebooks: [],
  currentNotebook: null,
  selectedSourceIds: new Set(),
  sourceSearchQuery: "",
  sourcesCollapsed: false,
  loading: false,
};

const $ = (id) => document.getElementById(id);

async function api(path, options = {}) {
  const response = await fetch(path, options);
  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("application/json") ? await response.json() : null;

  if (!response.ok) {
    throw new Error(data?.detail || `Request failed (${response.status})`);
  }

  return data;
}

function setLoading(loading) {
  state.loading = loading;
  $("sendButton").disabled = loading;
  $("questionInput").disabled = loading;
  $("addSourceButton").disabled = loading;
  $("attachButton").disabled = loading;
  document.body.classList.toggle("is-loading", loading);
}

function showError(error) {
  const message = error instanceof Error ? error.message : String(error);
  const node = document.createElement("div");
  node.className = "error-banner";
  node.textContent = message;
  document.body.appendChild(node);
  setTimeout(() => node.remove(), 4500);
}

function showPage(id) {
  ["notebooksPage", "notebookPage"].forEach((pageId) => {
    $(pageId).classList.toggle("hidden", pageId !== id);
  });
}

function renderNotebooks() {
  const grid = $("notebookGrid");

  if (!state.notebooks.length) {
    grid.innerHTML = `<div class="source-empty">No notebooks yet.</div>`;
    return;
  }

  grid.innerHTML = state.notebooks.map((book) => `
    <button class="notebook-card" type="button" data-notebook-id="${book.id}">
      <div class="card-icon">${escapeHtml(book.icon)}</div>
      <h3>${escapeHtml(book.name)}</h3>
      <p>${escapeHtml(book.description)}</p>
      <div class="card-footer">
        <span>${book.source_count} sources</span>
        <span>Open →</span>
      </div>
    </button>
  `).join("");

  grid.querySelectorAll("[data-notebook-id]").forEach((card) => {
    card.addEventListener("click", () => openNotebook(Number(card.dataset.notebookId)));
  });
}

async function loadNotebooks() {
  state.notebooks = await api("/api/notebooks");
  renderNotebooks();

  const savedId = Number(localStorage.getItem("jerry.currentNotebookId"));
  if (savedId && state.notebooks.some((book) => book.id === savedId)) {
    await openNotebook(savedId);
  }
}

async function addNotebook() {
  const name = window.prompt("Enter notebook name:");
  if (!name?.trim()) return;

  try {
    const notebook = await api("/api/notebooks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: name.trim() }),
    });

    state.notebooks.push({ ...notebook, source_count: 0, sources: [] });
    state.notebooks.sort((a, b) => b.id - a.id);
    renderNotebooks();
    await openNotebook(notebook.id);
  } catch (error) {
    showError(error);
  }
}

async function openNotebook(id) {
  try {
    const notebook = await api(`/api/notebooks/${id}`);
    state.currentNotebook = notebook;
    state.selectedSourceIds = new Set();
    state.sourceSearchQuery = "";
    state.sourcesCollapsed = false;
    localStorage.setItem("jerry.currentNotebookId", String(id));

    $("currentIcon").textContent = notebook.icon;
    $("currentTitle").textContent = notebook.name;
    $("sourceDescription").textContent = notebook.description;
    refreshCurrentCount();

    showPage("notebookPage");
    $("sourceSearchInput").value = "";
    renderSources();
    updateSourcesPanelVisibility();
    await loadMessages();
  } catch (error) {
    showError(error);
  }
}

function goBack() {
  state.currentNotebook = null;
  localStorage.removeItem("jerry.currentNotebookId");
  showPage("notebooksPage");
  renderNotebooks();
}

function refreshCurrentCount() {
  if (!state.currentNotebook) return;
  $("currentCount").textContent = `${state.currentNotebook.sources.length} sources`;
}

function getVisibleSources() {
  const query = state.sourceSearchQuery;
  return state.currentNotebook.sources.filter((source) => {
    const text = `${source.title} ${source.detail} ${source.type}`.toLowerCase();
    return text.includes(query);
  });
}

function renderSources() {
  if (!state.currentNotebook) return;

  const list = $("sourceList");
  const empty = $("sourceEmptyState");
  const visibleSources = getVisibleSources();

  list.innerHTML = visibleSources.map((source) => `
    <label class="source-card ${state.selectedSourceIds.has(source.id) ? "selected" : ""}" data-source-id="${escapeHtml(source.id)}">
      <input class="source-check" type="checkbox" ${state.selectedSourceIds.has(source.id) ? "checked" : ""}>
      <div class="source-type">${escapeHtml(source.type)}</div>
      <div class="source-card-main">
        <div class="source-info">
          <strong>${escapeHtml(source.title)}</strong>
          <small>${escapeHtml(source.detail)}</small>
        </div>
      </div>
    </label>
  `).join("");

  const hasVisible = visibleSources.length > 0;
  list.classList.toggle("hidden", !hasVisible);
  empty.classList.toggle("hidden", hasVisible);

  list.querySelectorAll(".source-card").forEach((card) => {
    const checkbox = card.querySelector(".source-check");
    checkbox.addEventListener("change", () => {
      const sourceId = card.dataset.sourceId;
      if (checkbox.checked) state.selectedSourceIds.add(sourceId);
      else state.selectedSourceIds.delete(sourceId);
      syncSourceControls();
    });
  });

  syncSourceControls();
}

function syncSourceControls() {
  const visibleSources = getVisibleSources();
  const selectedVisibleCount = visibleSources.filter((source) => state.selectedSourceIds.has(source.id)).length;
  const checkbox = $("selectAllSourcesCheckbox");

  checkbox.checked = visibleSources.length > 0 && selectedVisibleCount === visibleSources.length;
  checkbox.indeterminate = selectedVisibleCount > 0 && selectedVisibleCount < visibleSources.length;
  $("removeSelectedButton").disabled = state.selectedSourceIds.size === 0;

  document.querySelectorAll(".source-card").forEach((card) => {
    card.classList.toggle("selected", state.selectedSourceIds.has(card.dataset.sourceId));
  });
}

async function uploadSource(file) {
  if (!state.currentNotebook || !file) return;

  const form = new FormData();
  form.append("file", file);

  try {
    setLoading(true);
    const source = await api(`/api/notebooks/${state.currentNotebook.id}/sources`, {
      method: "POST",
      body: form,
    });

    state.currentNotebook.sources.push(source);
    refreshCurrentCount();
    renderSources();
    await loadNotebooksSilently();
  } catch (error) {
    showError(error);
  } finally {
    setLoading(false);
    $("sourceFileInput").value = "";
  }
}

async function removeSelectedSources() {
  if (!state.currentNotebook || state.selectedSourceIds.size === 0) return;
  if (!window.confirm("Remove the selected sources?")) return;

  try {
    setLoading(true);
    for (const sourceId of state.selectedSourceIds) {
      await api(`/api/notebooks/${state.currentNotebook.id}/sources/${encodeURIComponent(sourceId)}`, {
        method: "DELETE",
      });
    }

    const selected = state.selectedSourceIds;
    state.currentNotebook.sources = state.currentNotebook.sources.filter((source) => !selected.has(source.id));
    state.selectedSourceIds = new Set();
    refreshCurrentCount();
    renderSources();
    await loadNotebooksSilently();
  } catch (error) {
    showError(error);
  } finally {
    setLoading(false);
  }
}

function handleSourceSearch(event) {
  state.sourceSearchQuery = event.target.value.trim().toLowerCase();
  renderSources();
}

function toggleSelectAllSources(event) {
  const checked = event.target.checked;
  getVisibleSources().forEach((source) => {
    if (checked) state.selectedSourceIds.add(source.id);
    else state.selectedSourceIds.delete(source.id);
  });
  renderSources();
}

function toggleSourcesPanel(forceOpen = false) {
  state.sourcesCollapsed = forceOpen ? false : !state.sourcesCollapsed;
  updateSourcesPanelVisibility();
}

function updateSourcesPanelVisibility() {
  const panel = document.querySelector(".sources");
  panel.classList.toggle("is-collapsed", state.sourcesCollapsed);
  $("openSourcesButton").classList.toggle("hidden", !state.sourcesCollapsed);
}

function appendUserMessage(text) {
  const messages = $("messages");
  const row = document.createElement("div");
  row.className = "message user";

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = "V";

  const bubble = document.createElement("div");
  bubble.className = "user-bubble";
  bubble.textContent = text;

  row.append(bubble, avatar);
  messages.appendChild(row);
  scrollChatToBottom();
}

function appendAssistantMessage(answer, citations) {
  const row = document.createElement("div");
  row.className = "message ai";

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = "✦";

  const answerBox = document.createElement("div");
  answerBox.className = "ai-answer";

  const title = document.createElement("h3");
  title.textContent = "Answer from your sources";

  const text = document.createElement("p");
  text.textContent = answer;

  answerBox.append(title, text);

  if (citations?.length) {
    const citationLabel = document.createElement("span");
    citationLabel.className = "citation";
    citationLabel.textContent = `Sources · ${citations.length} references`;
    answerBox.appendChild(citationLabel);

    const sourceWrap = document.createElement("div");
    sourceWrap.className = "citation-list";

    citations.forEach((citation) => {
      const details = document.createElement("details");
      details.className = "citation-item";

      const summary = document.createElement("summary");
      summary.textContent = `[${citation.id}] ${citation.source} (Chunk ${citation.chunk_id}/${citation.total_chunks})`;

      const content = document.createElement("p");
      content.textContent = citation.content;

      details.append(summary, content);
      sourceWrap.appendChild(details);
    });

    answerBox.appendChild(sourceWrap);
  }

  row.append(avatar, answerBox);
  $("messages").appendChild(row);
  scrollChatToBottom();
}

function appendThinkingMessage() {
  const row = document.createElement("div");
  row.className = "message ai thinking-message";
  row.id = "thinkingMessage";

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = "✦";

  const bubble = document.createElement("div");
  bubble.className = "ai-answer";
  bubble.textContent = "Thinking…";

  row.append(avatar, bubble);
  $("messages").appendChild(row);
  scrollChatToBottom();
}

function removeThinkingMessage() {
  $("thinkingMessage")?.remove();
}

async function loadMessages() {
  if (!state.currentNotebook) return;

  const messages = await api(`/api/notebooks/${state.currentNotebook.id}/messages`);
  $("messages").innerHTML = "";
  $("welcome").classList.toggle("hidden", messages.length > 0);

  messages.forEach((message) => {
    if (message.role === "human") appendUserMessage(message.content);
    else appendAssistantMessage(message.content, message.citations);
  });
}

async function sendMessage(questionOverride = null) {
  if (!state.currentNotebook || state.loading) return;

  const input = $("questionInput");
  const question = (questionOverride ?? input.value).trim();
  if (!question) return;

  $("welcome").classList.add("hidden");
  appendUserMessage(question);
  input.value = "";

  try {
    setLoading(true);
    appendThinkingMessage();

    const result = await api(`/api/notebooks/${state.currentNotebook.id}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });

    removeThinkingMessage();
    appendAssistantMessage(result.answer, result.citations);
  } catch (error) {
    removeThinkingMessage();
    showError(error);
  } finally {
    setLoading(false);
    input.focus();
  }
}

async function loadNotebooksSilently() {
  state.notebooks = await api("/api/notebooks");
  if (!state.currentNotebook) renderNotebooks();
}

function scrollChatToBottom() {
  const chat = document.querySelector(".chat-inner");
  chat.scrollTop = chat.scrollHeight;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function bindEvents() {
  $("newNotebookButton").addEventListener("click", addNotebook);
  $("backButton").addEventListener("click", goBack);
  $("addSourceButton").addEventListener("click", () => $("sourceFileInput").click());
  $("attachButton").addEventListener("click", () => $("sourceFileInput").click());
  $("sourceFileInput").addEventListener("change", (event) => uploadSource(event.target.files?.[0]));
  $("sourceSearchInput").addEventListener("input", handleSourceSearch);
  $("selectAllSourcesCheckbox").addEventListener("change", toggleSelectAllSources);
  $("removeSelectedButton").addEventListener("click", removeSelectedSources);
  $("collapseSourcesButton").addEventListener("click", () => toggleSourcesPanel());
  $("openSourcesButton").addEventListener("click", () => toggleSourcesPanel(true));
  $("sendButton").addEventListener("click", () => sendMessage());

  $("questionInput").addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  });

  document.querySelectorAll("[data-question]").forEach((button) => {
    button.addEventListener("click", () => sendMessage(button.dataset.question));
  });
}

async function boot() {
  try {
    bindEvents();
    showPage("notebooksPage");
    await loadNotebooks();
  } catch (error) {
    showError(error);
  }
}

document.addEventListener("DOMContentLoaded", boot);
