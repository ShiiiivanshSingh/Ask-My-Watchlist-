const form = document.getElementById("ask-form");
const input = document.getElementById("query");
const ticketsEl = document.getElementById("tickets");
const emptyState = document.getElementById("empty-state");

let serial = 0;

const sourceLabels = {
  kb: "from your reviews",
  cache: "replayed from cache",
  api: "fresh from groq",
};

function addTicket(question) {
  serial += 1;
  const ticket = document.createElement("div");
  ticket.className = "ticket loading";
  ticket.innerHTML = `
    <div class="ticket-serial">No. ${String(serial).padStart(4, "0")}</div>
    <p class="ticket-question">${escapeHtml(question)}</p>
    <div class="ticket-answer">thinking…</div>
    <div class="ticket-footer"></div>
  `;
  emptyState.classList.add("hidden");
  ticketsEl.prepend(ticket);
  return ticket;
}

function fillTicket(ticket, data) {
  ticket.classList.remove("loading");
  const answerEl = ticket.querySelector(".ticket-answer");
  const footerEl = ticket.querySelector(".ticket-footer");

  if (data.error) {
    answerEl.textContent = "Couldn't find an answer for that.";
    return;
  }

  answerEl.textContent = data.answer;
  const label = sourceLabels[data.source] || data.source;
  footerEl.innerHTML = `<span class="stamp ${data.source}">${label}</span>`;
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const query = input.value.trim();
  if (!query) return;

  input.value = "";
  const ticket = addTicket(query);

  try {
    const res = await fetch("/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });
    const data = await res.json();
    fillTicket(ticket, data);
  } catch (err) {
    fillTicket(ticket, { error: true });
  }
});
