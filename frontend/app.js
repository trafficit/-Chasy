"use strict";

const $ = (id) => document.getElementById(id);
const api = (path, opts) =>
  fetch(path, { credentials: "same-origin", ...opts });

let entries = [];
let selectedId = null;
let editingId = null;

// --------------------------------------------------------------------------- //
// helpers
// --------------------------------------------------------------------------- //
function toast(msg) {
  const t = $("toast");
  t.textContent = msg;
  t.hidden = false;
  clearTimeout(toast._t);
  toast._t = setTimeout(() => (t.hidden = true), 3000);
}

function isoToDots(iso) {
  // "2026-09-09" -> "09.09.2026"
  const [y, m, d] = iso.split("-");
  return `${d}.${m}.${y}`;
}

function dotsToIso(dots) {
  const m = String(dots).match(/^(\d{2})\.(\d{2})\.(\d{4})/);
  return m ? `${m[3]}-${m[2]}-${m[1]}` : "";
}

function minutes(hhmm) {
  const m = String(hhmm).match(/^(\d+):(\d+)$/);
  return m ? +m[1] * 60 + +m[2] : 0;
}

// --------------------------------------------------------------------------- //
// rendering
// --------------------------------------------------------------------------- //
function render() {
  const list = $("list");
  list.innerHTML = "";
  const lunchShown = entries.some(
    (e) => e.lunch && !e.date.includes("Holiday")
  );

  for (const e of entries) {
    const li = document.createElement("li");
    li.dataset.id = e.id;
    if (e.id === selectedId) li.classList.add("sel");

    const main = document.createElement("div");
    main.className = "main";
    main.textContent = `${e.date}   ${e.start}–${e.end} → ${e.duration}`;

    const sub = document.createElement("div");
    sub.className = "sub";
    const bits = [];
    if (lunchShown && e.lunch) bits.push(`Обед ${e.lunch}`);
    if (lunchShown) bits.push(`Net ${e.net}`);
    if (e.comment) bits.push(`✎ ${e.comment}`);
    sub.textContent = bits.join("   ·   ");

    li.append(main, sub);
    li.addEventListener("click", () => {
      selectedId = selectedId === e.id ? null : e.id;
      render();
    });
    list.append(li);
  }

  $("empty").hidden = entries.length > 0;

  const total = entries.reduce((s, e) => s + minutes(e.net), 0);
  $("total").textContent =
    `Net Total: ${Math.floor(total / 60)} hours and ${total % 60} minutes`;

  const idx = entries.findIndex((e) => e.id === selectedId);
  const has = idx >= 0;
  $("up").disabled = !has || idx === 0;
  $("down").disabled = !has || idx === entries.length - 1;
  $("edit").disabled = !has;
  $("del").disabled = !has;
}

// --------------------------------------------------------------------------- //
// data ops
// --------------------------------------------------------------------------- //
async function load() {
  const r = await api("/api/entries");
  if (r.status === 401) return showLogin();
  entries = await r.json();
  render();
}

function formPayload() {
  const dateIso = $("f-date").value;
  return {
    date: dateIso ? isoToDots(dateIso) : "",
    start: $("f-start").value || "00:00",
    end: $("f-end").value || "00:00",
    lunch: $("f-lunch").value.trim(),
    comment: $("f-comment").value.trim(),
  };
}

function clearForm() {
  ["f-date", "f-start", "f-end", "f-lunch", "f-comment"].forEach(
    (id) => ($(id).value = "")
  );
}

async function addEntry() {
  const body = formPayload();
  if (!body.date) return toast("Укажите дату");
  const r = await api("/api/entries", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) return toast((await r.json()).detail || "Ошибка");
  clearForm();
  await load();
}

async function addHoliday() {
  const iso = $("f-date").value;
  const base = iso ? isoToDots(iso) : isoToDots(new Date().toISOString().slice(0, 10));
  const r = await api("/api/entries", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ date: `${base} (Holiday)` }),
  });
  if (!r.ok) return toast("Ошибка");
  await load();
}

function startEdit() {
  const e = entries.find((x) => x.id === selectedId);
  if (!e) return;
  editingId = e.id;
  $("f-date").value = dotsToIso(e.date);
  $("f-start").value = /^\d{2}:\d{2}$/.test(e.start) ? e.start : "";
  $("f-end").value = /^\d{2}:\d{2}$/.test(e.end) ? e.end : "";
  $("f-lunch").value = e.lunch || "";
  $("f-comment").value = e.comment || "";
  $("add").hidden = true;
  $("holiday").hidden = true;
  $("save-edit").hidden = false;
  $("cancel-edit").hidden = false;
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function stopEdit() {
  editingId = null;
  clearForm();
  $("add").hidden = false;
  $("holiday").hidden = false;
  $("save-edit").hidden = true;
  $("cancel-edit").hidden = true;
}

async function saveEdit() {
  const body = formPayload();
  if (!body.date) return toast("Укажите дату");
  const r = await api(`/api/entries/${editingId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) return toast((await r.json()).detail || "Ошибка");
  stopEdit();
  await load();
}

async function del() {
  if (!selectedId) return;
  const r = await api(`/api/entries/${selectedId}`, { method: "DELETE" });
  if (!r.ok && r.status !== 204) return toast("Ошибка");
  selectedId = null;
  await load();
}

async function move(dir) {
  const idx = entries.findIndex((e) => e.id === selectedId);
  const j = idx + dir;
  if (idx < 0 || j < 0 || j >= entries.length) return;
  [entries[idx], entries[j]] = [entries[j], entries[idx]];
  render();
  await api("/api/entries/reorder", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ids: entries.map((e) => e.id) }),
  });
}

async function importFile(file) {
  const fd = new FormData();
  fd.append("file", file);
  const r = await api("/api/import", { method: "POST", body: fd });
  if (!r.ok) return toast((await r.json()).detail || "Не удалось прочитать файл");
  const { imported } = await r.json();
  toast(`Импортировано записей: ${imported}`);
  await load();
}

// --------------------------------------------------------------------------- //
// auth views
// --------------------------------------------------------------------------- //
function showLogin() {
  $("app").hidden = true;
  $("login").hidden = false;
}

async function showApp(email) {
  $("login").hidden = true;
  $("app").hidden = false;
  $("who").textContent = email;
  await load();
}

// --------------------------------------------------------------------------- //
// wire up
// --------------------------------------------------------------------------- //
$("login-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const email = $("login-email").value.trim();
  if (!email) return;
  const r = await api("/api/auth/request", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  if (r.ok) $("login-sent").hidden = false;
  else toast("Не удалось отправить письмо");
});

$("logout").addEventListener("click", async () => {
  await api("/api/auth/logout", { method: "POST" });
  location.href = "/";
});

$("add").addEventListener("click", addEntry);
$("holiday").addEventListener("click", addHoliday);
$("edit").addEventListener("click", startEdit);
$("save-edit").addEventListener("click", saveEdit);
$("cancel-edit").addEventListener("click", stopEdit);
$("del").addEventListener("click", del);
$("up").addEventListener("click", () => move(-1));
$("down").addEventListener("click", () => move(1));
$("export").addEventListener("click", () => (location.href = "/api/export.xlsx"));
$("import-btn").addEventListener("click", () => $("import-file").click());
$("import-file").addEventListener("change", (ev) => {
  if (ev.target.files[0]) importFile(ev.target.files[0]);
  ev.target.value = "";
});

(async function init() {
  const params = new URLSearchParams(location.search);
  if (params.get("error") === "link") {
    toast("Ссылка недействительна или устарела — запросите новую");
    history.replaceState({}, "", "/");
  }
  const r = await api("/api/me");
  if (r.ok) {
    const { email } = await r.json();
    showApp(email);
  } else {
    showLogin();
  }
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js").catch(() => {});
  }
})();
