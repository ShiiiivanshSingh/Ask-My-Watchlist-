const form = document.getElementById("ask-form");
const input = document.getElementById("query");
const ticketsEl = document.getElementById("tickets");
const emptyState = document.getElementById("empty-state");

const sidebar = document.getElementById("sidebar");
const sidebarCollapse = document.getElementById("sidebar-collapse");
const sidebarExpand = document.getElementById("sidebar-expand");
const historyList = document.getElementById("history-list");
const historyEmpty = document.getElementById("history-empty");

const settingsBtn = document.getElementById("settings-btn");
const settingsPanel = document.getElementById("settings-panel");
const cacheSizeLabel = document.getElementById("cache-size-label");
const clearCacheBtn = document.getElementById("clear-cache-btn");

const terminalFab = document.getElementById("terminal-fab");
const terminalPanel = document.getElementById("terminal-panel");
const terminalClose = document.getElementById("terminal-close");
const terminalBody = document.getElementById("terminal-body");

const HISTORY_KEY = "askShelfHistory";
let ticketCount = 0;
let apiCallCount = 0;

function loadHistory() {
  try {
    return JSON.parse(localStorage.getItem(HISTORY_KEY)) || [];
  } catch (e) {
    return [];
  }
}

function saveHistory(entries) {
  localStorage.setItem(HISTORY_KEY, JSON.stringify(entries.slice(0, 50)));
}

function pushHistory(query) {
  const entries = loadHistory();
  entries.unshift({ query, ts: Date.now() });
  saveHistory(entries);
}

function renderHistory() {
  const entries = loadHistory();
  historyList.innerHTML = "";
  if (entries.length === 0) {
    historyEmpty.style.display = "block";
    return;
  }
  historyEmpty.style.display = "none";
  for (const entry of entries) {
    const li = document.createElement("li");
    li.className = "history-item";
    const span = document.createElement("span");
    span.textContent = entry.query;
    li.appendChild(span);
    li.addEventListener("click", () => {
      input.value = entry.query;
      form.requestSubmit();
    });
    historyList.appendChild(li);
  }
}

function openOverlay(el) {
  el.classList.remove("hidden");
}

function closeOverlay(el) {
  el.classList.add("hidden");
}

const SIDEBAR_KEY = "askShelfSidebarOpen";

function setSidebarOpen(open) {
  if (open) {
    sidebar.classList.remove("hidden");
    sidebarExpand.classList.add("hidden");
    document.body.classList.remove("sidebar-collapsed");
  } else {
    sidebar.classList.add("hidden");
    sidebarExpand.classList.remove("hidden");
    document.body.classList.add("sidebar-collapsed");
  }
  localStorage.setItem(SIDEBAR_KEY, open ? "1" : "0");
}

sidebarCollapse.addEventListener("click", () => setSidebarOpen(false));
sidebarExpand.addEventListener("click", () => setSidebarOpen(true));

setSidebarOpen(localStorage.getItem(SIDEBAR_KEY) === "1");

settingsBtn.addEventListener("click", () => {
  refreshStats();
  openOverlay(settingsPanel);
});

document.querySelectorAll("[data-close]").forEach((el) => {
  el.addEventListener("click", () => {
    closeOverlay(document.getElementById(el.dataset.close));
  });
});

renderHistory();

async function refreshStats() {
  try {
    const res = await fetch("/stats");
    const data = await res.json();
    cacheSizeLabel.textContent = `${data.cache_size} entries`;
  } catch (e) {
    cacheSizeLabel.textContent = "unavailable";
  }
}

clearCacheBtn.addEventListener("click", async () => {
  const confirmed = window.confirm("Clear the semantic cache? This can't be undone.");
  if (!confirmed) return;
  clearCacheBtn.disabled = true;
  try {
    const res = await fetch("/clear-cache", { method: "POST" });
    const data = await res.json();
    cacheSizeLabel.textContent = `${data.cache_size} entries`;
    appendTerminal(`$ cache cleared -- removed ${data.cleared} entries`, "terminal-muted");
  } catch (e) {
    appendTerminal("$ failed to clear cache", "terminal-api");
  }
  clearCacheBtn.disabled = false;
});

terminalFab.addEventListener("click", () => {
  terminalPanel.classList.toggle("hidden");
});

terminalClose.addEventListener("click", () => {
  terminalPanel.classList.add("hidden");
});

function appendTerminal(text, cls) {
  const line = document.createElement("div");
  line.className = `terminal-line ${cls || ""}`.trim();
  line.textContent = text;
  terminalBody.appendChild(line);
  terminalBody.scrollTop = terminalBody.scrollHeight;
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function inlineFormat(text) {
  return escapeHtml(text)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/(?<!\*)\*([^*]+)\*(?!\*)/g, "<em>$1</em>");
}

function renderMarkdownLite(text) {
  const lines = text.split("\n");
  const blocks = [];
  let listBuffer = [];
  let listType = null;

  function flushList() {
    if (listBuffer.length === 0) return;
    const tag = listType === "ol" ? "ol" : "ul";
    blocks.push(`<${tag}>${listBuffer.map((li) => `<li>${inlineFormat(li)}</li>`).join("")}</${tag}>`);
    listBuffer = [];
    listType = null;
  }

  for (const raw of lines) {
    const line = raw.trim();
    if (!line) {
      flushList();
      continue;
    }
    const numbered = line.match(/^\d+\.\s+(.*)/);
    const bulleted = line.match(/^[-*]\s+(.*)/);
    if (numbered) {
      if (listType !== "ol") flushList();
      listType = "ol";
      listBuffer.push(numbered[1]);
    } else if (bulleted) {
      if (listType !== "ul") flushList();
      listType = "ul";
      listBuffer.push(bulleted[1]);
    } else {
      flushList();
      blocks.push(`<p>${inlineFormat(line)}</p>`);
    }
  }
  flushList();
  return blocks.join("");
}

function truncate(text, max) {
  if (!text) return "";
  return text.length > max ? text.slice(0, max) + "..." : text;
}

function logInsights(query, result) {
  appendTerminal(`$ query: "${query}"`, "terminal-query");
  const sourceCls = result.source === "cache" ? "terminal-cache" : "terminal-api";
  appendTerminal(`> source: ${result.source} (score ${result.score.toFixed(3)})`, sourceCls);
  if (result.source === "cache" && result.cached_from) {
    appendTerminal(`> originally answered from: ${result.cached_from}`, "terminal-muted");
  }
  if (result.context) {
    appendTerminal(`> context retrieved:\n${truncate(result.context, 400)}`, "terminal-muted");
  }
  if (result.source === "kb" || result.source === "api") {
    apiCallCount += 1;
    appendTerminal(`> groq api calls this session: ${apiCallCount}`, "terminal-api");
  }
}

function stampLabel(source) {
  if (source === "kb") return "knowledge base";
  if (source === "cache") return "cache";
  return "no match";
}

function createTicket(query) {
  ticketCount += 1;
  const serial = String(ticketCount).padStart(4, "0");
  const ticket = document.createElement("div");
  ticket.className = "ticket loading";

  const serialEl = document.createElement("div");
  serialEl.className = "ticket-serial";
  serialEl.textContent = `No. ${serial}`;

  const questionEl = document.createElement("p");
  questionEl.className = "ticket-question";
  questionEl.textContent = query;

  const answerEl = document.createElement("div");
  answerEl.className = "ticket-answer";
  answerEl.textContent = "Flipping back through Shivansh's diary...";

  const footer = document.createElement("div");
  footer.className = "ticket-footer";

  ticket.appendChild(serialEl);
  ticket.appendChild(questionEl);
  ticket.appendChild(answerEl);
  ticket.appendChild(footer);
  ticketsEl.prepend(ticket);

  return { ticket, serialEl, answerEl, footer };
}

function finishTicket(refs, result) {
  refs.ticket.classList.remove("loading");
  refs.answerEl.innerHTML = renderMarkdownLite(result.answer);
  if (result.source === "api" || result.source === "kb") {
    refs.serialEl.classList.add("ticket-serial-api");
  }
  const stamp = document.createElement("span");
  stamp.className = `stamp ${result.source}`;
  stamp.textContent = stampLabel(result.source);
  refs.footer.appendChild(stamp);
}

document.querySelectorAll(".quick-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    input.value = btn.dataset.query;
    form.requestSubmit();
  });
});

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const query = input.value.trim();
  if (!query) return;

  emptyState.classList.add("hidden");
  const refs = createTicket(query);
  input.value = "";
  pushHistory(query);
  renderHistory();

  try {
    const res = await fetch("/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });
    const result = await res.json();
    if (result.error) {
      refs.ticket.classList.remove("loading");
      refs.answerEl.textContent = result.error;
      appendTerminal(`$ error: ${result.error}`, "terminal-api");
      return;
    }
    finishTicket(refs, result);
    logInsights(query, result);
  } catch (err) {
    refs.ticket.classList.remove("loading");
    refs.answerEl.textContent = "Something went wrong reaching the server.";
    appendTerminal(`$ request failed: ${err}`, "terminal-api");
  }
});