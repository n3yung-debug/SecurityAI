"use strict";

// ---- helpers -------------------------------------------------------
const $ = (sel) => document.querySelector(sel);

async function api(path, options) {
  const res = await fetch(path, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || "Something went wrong.");
  return data;
}

function toast(msg) {
  const t = $("#toast");
  t.textContent = msg;
  t.classList.remove("hidden");
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => t.classList.add("hidden"), 2600);
}

function escapeHtml(s) {
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

function confidenceClass(score) {
  if (score >= 0.45) return "high";
  if (score >= 0.28) return "med";
  return "low";
}
function confidenceLabel(score) {
  if (score >= 0.45) return "High confidence";
  if (score >= 0.28) return "Medium confidence";
  return "Low confidence";
}

// ---- tabs ----------------------------------------------------------
document.querySelectorAll(".tab").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    $("#" + btn.dataset.tab).classList.add("active");
    if (btn.dataset.tab === "manage") {
      loadQa();
      loadDocs();
    }
  });
});

// ---- ask -----------------------------------------------------------
async function ask() {
  const q = $("#question").value.trim();
  if (!q) return;
  $("#emptyHint").classList.add("hidden");
  const box = $("#answer");
  box.classList.remove("hidden", "notfound");
  box.innerHTML = '<div class="answer-text">Searching…</div>';

  try {
    const data = await api("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: q }),
    });
    renderAnswer(data);
  } catch (e) {
    box.classList.add("notfound");
    box.innerHTML = `<div class="answer-text">${escapeHtml(e.message)}</div>`;
  }
}

function renderAnswer(data) {
  const box = $("#answer");
  box.classList.remove("notfound");

  if (!data.found) {
    box.classList.add("notfound");
    let html = `<div class="answer-text">${escapeHtml(data.message)}</div>`;
    if (data.suggestions && data.suggestions.length) {
      html += `<div class="alts"><h4>Closest matches</h4>`;
      data.suggestions.forEach((s) => {
        html += `<div class="alt">${escapeHtml(s.answer)}
                 <div class="alt-src">${escapeHtml(s.source)}</div></div>`;
      });
      html += `</div>`;
    }
    box.innerHTML = html;
    return;
  }

  const cls = confidenceClass(data.confidence);
  let html = `<div class="answer-text">${escapeHtml(data.answer)}</div>`;
  html += `<div class="meta">
             <span class="badge ${cls}">${confidenceLabel(data.confidence)}</span>
             <span>Source: ${escapeHtml(data.source)}</span>
           </div>`;

  if (data.alternatives && data.alternatives.length) {
    html += `<div class="alts"><h4>Other possible answers</h4>`;
    data.alternatives.forEach((a) => {
      html += `<div class="alt">${escapeHtml(a.answer)}
               <div class="alt-src">${escapeHtml(a.source)}</div></div>`;
    });
    html += `</div>`;
  }
  box.innerHTML = html;
}

$("#askBtn").addEventListener("click", ask);
$("#question").addEventListener("keydown", (e) => {
  if (e.key === "Enter") ask();
});

// ---- Q&A management ------------------------------------------------
async function loadQa() {
  const list = $("#qaList");
  const items = await api("/api/qa");
  if (!items.length) {
    list.innerHTML = '<div class="hint">No Q&A pairs yet.</div>';
    return;
  }
  list.innerHTML = items
    .map(
      (it) => `
      <div class="list-item" data-id="${it.id}">
        <div class="li-title">${escapeHtml(it.question)}</div>
        <div class="li-sub">${escapeHtml(it.answer)}</div>
        <div class="li-actions">
          <button class="edit">Edit</button>
          <button class="del">Delete</button>
        </div>
      </div>`
    )
    .join("");

  list.querySelectorAll(".del").forEach((b) =>
    b.addEventListener("click", async (e) => {
      const id = e.target.closest(".list-item").dataset.id;
      await api(`/api/qa/${id}`, { method: "DELETE" });
      toast("Deleted");
      loadQa();
    })
  );
  list.querySelectorAll(".edit").forEach((b) =>
    b.addEventListener("click", (e) => {
      const card = e.target.closest(".list-item");
      const id = card.dataset.id;
      const q = card.querySelector(".li-title").textContent;
      const a = card.querySelector(".li-sub").textContent;
      const nq = prompt("Edit question:", q);
      if (nq === null) return;
      const na = prompt("Edit answer:", a);
      if (na === null) return;
      api(`/api/qa/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: nq, answer: na }),
      }).then(() => {
        toast("Updated");
        loadQa();
      });
    })
  );
}

$("#addQaBtn").addEventListener("click", async () => {
  const question = $("#qaQuestion").value.trim();
  const answer = $("#qaAnswer").value.trim();
  if (!question || !answer) {
    toast("Please fill in both fields.");
    return;
  }
  try {
    await api("/api/qa", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, answer }),
    });
    $("#qaQuestion").value = "";
    $("#qaAnswer").value = "";
    toast("Q&A added");
    loadQa();
  } catch (e) {
    toast(e.message);
  }
});

// ---- document management -------------------------------------------
async function loadDocs() {
  const list = $("#docList");
  const items = await api("/api/documents");
  if (!items.length) {
    list.innerHTML = '<div class="hint">No documents uploaded yet.</div>';
    return;
  }
  list.innerHTML = items
    .map(
      (it) => `
      <div class="list-item" data-id="${it.id}">
        <div class="li-title">${escapeHtml(it.filename)}</div>
        <div class="li-sub">${it.chunk_count} searchable passage(s)</div>
        <div class="li-actions">
          <button class="del">Remove</button>
        </div>
      </div>`
    )
    .join("");
  list.querySelectorAll(".del").forEach((b) =>
    b.addEventListener("click", async (e) => {
      const id = e.target.closest(".list-item").dataset.id;
      await api(`/api/documents/${id}`, { method: "DELETE" });
      toast("Removed");
      loadDocs();
    })
  );
}

$("#fileInput").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const status = $("#uploadStatus");
  status.textContent = `Reading "${file.name}"…`;
  const form = new FormData();
  form.append("file", file);
  try {
    const res = await api("/api/documents", { method: "POST", body: form });
    status.textContent = `Added "${file.name}" (${res.chunk_count} passages).`;
    toast("Document added");
    loadDocs();
  } catch (err) {
    status.textContent = err.message;
  } finally {
    e.target.value = "";
  }
});
