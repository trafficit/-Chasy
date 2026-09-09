"use strict";

const $ = (id) => document.getElementById(id);
const api = (path, opts) =>
  fetch(path, { credentials: "same-origin", ...opts });

const APP_VERSION = "1.0";
// shown in the About dialog; change the number here only
const APP_PRICE = "7 €";

let entries = [];
let selectedId = null;
let editingId = null;
let addBusy = false;

// --------------------------------------------------------------------------- //
// i18n
// --------------------------------------------------------------------------- //
const I18N = {
  ru: {
    logout: "выйти",
    login_hint: "Введите рабочую почту — пришлём ссылку для входа.",
    login_btn: "Получить ссылку",
    login_sent: "Письмо отправлено. Откройте ссылку из письма на этом устройстве.",
    f_date: "Дата",
    f_start: "Начало",
    f_end: "Конец",
    f_lunch: "Обед (мин или Ч:ММ)",
    f_comment: "Комментарий",
    ph_comment: "заметка",
    add: "Добавить",
    holiday: "Выходной",
    save_edit: "Сохранить изменения",
    cancel: "отмена",
    empty: "Пока нет записей.",
    move_up: "⬆ Выше",
    move_down: "⬇ Ниже",
    edit: "✏️ Изменить",
    del: "🗑 Удалить",
    export: "Экспорт в Excel",
    import: "Импорт из Excel",
    lunch_label: "Обед",
    net_label: "Нетто",
    total: "Всего (нетто): {h} ч {m} мин",
    holiday_tag: "Выходной",
    err_no_date: "Укажите дату",
    err_dup: "Такая запись уже есть",
    err_generic: "Ошибка",
    err_import: "Не удалось прочитать файл",
    imported: "Импортировано записей: {n}",
    err_mail: "Не удалось отправить письмо",
    err_link: "Ссылка недействительна или устарела — запросите новую",
    about: "О приложении",
    about_desc:
      "Учёт рабочих часов: вход по ссылке из письма, у каждого свой журнал, экспорт и импорт Excel.",
    about_contact: "Связь",
    about_close: "Закрыть",
    lic_gate_title: "Доступ по коду",
    lic_gate_hint: "Введите код доступа, который вам выдали.",
    lic_redeem: "Активировать",
    lic_activated: "Доступ активирован",
    lic_err_unknown_code: "Код не найден",
    lic_err_revoked_code: "Код отключён",
    lic_err_expired_code: "Срок действия кода истёк",
    lic_err_seats_full: "Достигнут лимит пользователей по этому коду",
    lic_need_active: "Нужен активный код доступа",
    lic_banner_expired: "Доступ истёк {date}. Добавление записей отключено — продлите код.",
    lic_banner_revoked: "Код доступа отключён. Свяжитесь с администратором:",
    lic_banner_trial: "Пробный период до {date}.",
    lic_banner_soon: "Доступ действует до {date}.",
    lic_tos_label: "Я принимаю",
    lic_tos_link: "условия использования",
    lic_tos_required: "Примите условия использования",
    about_terms: "Условия использования",
    about_price: "{price}/мес за компанию · 14 дней бесплатно · продление автоматическое, отмена в любой момент",
  },
  uk: {
    logout: "вийти",
    login_hint: "Введіть робочу пошту — надішлемо посилання для входу.",
    login_btn: "Отримати посилання",
    login_sent: "Лист надіслано. Відкрийте посилання з листа на цьому пристрої.",
    f_date: "Дата",
    f_start: "Початок",
    f_end: "Кінець",
    f_lunch: "Обід (хв або Г:ХХ)",
    f_comment: "Коментар",
    ph_comment: "нотатка",
    add: "Додати",
    holiday: "Вихідний",
    save_edit: "Зберегти зміни",
    cancel: "скасувати",
    empty: "Поки немає записів.",
    move_up: "⬆ Вище",
    move_down: "⬇ Нижче",
    edit: "✏️ Змінити",
    del: "🗑 Видалити",
    export: "Експорт у Excel",
    import: "Імпорт з Excel",
    lunch_label: "Обід",
    net_label: "Нетто",
    total: "Разом (нетто): {h} год {m} хв",
    holiday_tag: "Вихідний",
    err_no_date: "Вкажіть дату",
    err_dup: "Такий запис уже є",
    err_generic: "Помилка",
    err_import: "Не вдалося прочитати файл",
    imported: "Імпортовано записів: {n}",
    err_mail: "Не вдалося надіслати лист",
    err_link: "Посилання недійсне або застаріле — запросіть нове",
    about: "Про застосунок",
    about_desc:
      "Облік робочих годин: вхід за посиланням з листа, у кожного свій журнал, експорт та імпорт Excel.",
    about_contact: "Зв'язок",
    about_close: "Закрити",
    lic_gate_title: "Доступ за кодом",
    lic_gate_hint: "Введіть код доступу, який вам видали.",
    lic_redeem: "Активувати",
    lic_activated: "Доступ активовано",
    lic_err_unknown_code: "Код не знайдено",
    lic_err_revoked_code: "Код вимкнено",
    lic_err_expired_code: "Термін дії коду минув",
    lic_err_seats_full: "Досягнуто ліміту користувачів за цим кодом",
    lic_need_active: "Потрібен активний код доступу",
    lic_banner_expired: "Доступ закінчився {date}. Додавання записів вимкнено — продовжте код.",
    lic_banner_revoked: "Код доступу вимкнено. Зв'яжіться з адміністратором:",
    lic_banner_trial: "Пробний період до {date}.",
    lic_banner_soon: "Доступ діє до {date}.",
    lic_tos_label: "Я приймаю",
    lic_tos_link: "умови використання",
    lic_tos_required: "Прийміть умови використання",
    about_terms: "Умови використання",
    about_price: "{price}/міс за компанію · 14 днів безкоштовно · продовження автоматичне, скасування будь-коли",
  },
  sk: {
    logout: "odhlásiť",
    login_hint: "Zadajte pracovný e-mail — pošleme odkaz na prihlásenie.",
    login_btn: "Získať odkaz",
    login_sent: "E-mail odoslaný. Otvorte odkaz z e-mailu na tomto zariadení.",
    f_date: "Dátum",
    f_start: "Začiatok",
    f_end: "Koniec",
    f_lunch: "Obed (min alebo H:MM)",
    f_comment: "Poznámka",
    ph_comment: "poznámka",
    add: "Pridať",
    holiday: "Sviatok",
    save_edit: "Uložiť zmeny",
    cancel: "zrušiť",
    empty: "Zatiaľ žiadne záznamy.",
    move_up: "⬆ Vyššie",
    move_down: "⬇ Nižšie",
    edit: "✏️ Upraviť",
    del: "🗑 Odstrániť",
    export: "Export do Excelu",
    import: "Import z Excelu",
    lunch_label: "Obed",
    net_label: "Netto",
    total: "Spolu (netto): {h} h {m} min",
    holiday_tag: "Sviatok",
    err_no_date: "Zadajte dátum",
    err_dup: "Takýto záznam už existuje",
    err_generic: "Chyba",
    err_import: "Súbor sa nepodarilo načítať",
    imported: "Importovaných záznamov: {n}",
    err_mail: "E-mail sa nepodarilo odoslať",
    err_link: "Odkaz je neplatný alebo vypršal — vyžiadajte si nový",
    about: "O aplikácii",
    about_desc:
      "Evidencia pracovného času: prihlásenie cez odkaz v e-maile, každý má vlastný denník, export a import Excelu.",
    about_contact: "Kontakt",
    about_close: "Zavrieť",
    lic_gate_title: "Prístup cez kód",
    lic_gate_hint: "Zadajte prístupový kód, ktorý ste dostali.",
    lic_redeem: "Aktivovať",
    lic_activated: "Prístup aktivovaný",
    lic_err_unknown_code: "Kód sa nenašiel",
    lic_err_revoked_code: "Kód je vypnutý",
    lic_err_expired_code: "Platnosť kódu vypršala",
    lic_err_seats_full: "Dosiahnutý limit používateľov pre tento kód",
    lic_need_active: "Potrebný je platný prístupový kód",
    lic_banner_expired: "Prístup vypršal {date}. Pridávanie záznamov je vypnuté — obnovte kód.",
    lic_banner_revoked: "Prístupový kód je vypnutý. Kontaktujte správcu:",
    lic_banner_trial: "Skúšobné obdobie do {date}.",
    lic_banner_soon: "Prístup platí do {date}.",
    lic_tos_label: "Súhlasím s",
    lic_tos_link: "podmienkami používania",
    lic_tos_required: "Potvrďte podmienky používania",
    about_terms: "Podmienky používania",
    about_price: "{price}/mes. za firmu · 14 dní zdarma · automatické obnovenie, zrušenie kedykoľvek",
  },
  en: {
    logout: "sign out",
    login_hint: "Enter your work e-mail — we'll send a sign-in link.",
    login_btn: "Send link",
    login_sent: "E-mail sent. Open the link from the message on this device.",
    f_date: "Date",
    f_start: "Start",
    f_end: "End",
    f_lunch: "Lunch (min or H:MM)",
    f_comment: "Comment",
    ph_comment: "note",
    add: "Add",
    holiday: "Day off",
    save_edit: "Save changes",
    cancel: "cancel",
    empty: "No entries yet.",
    move_up: "⬆ Up",
    move_down: "⬇ Down",
    edit: "✏️ Edit",
    del: "🗑 Delete",
    export: "Export to Excel",
    import: "Import from Excel",
    lunch_label: "Lunch",
    net_label: "Net",
    total: "Net total: {h}h {m}m",
    holiday_tag: "Day off",
    err_no_date: "Enter a date",
    err_dup: "This entry already exists",
    err_generic: "Error",
    err_import: "Could not read the file",
    imported: "Imported entries: {n}",
    err_mail: "Could not send the e-mail",
    err_link: "The link is invalid or expired — request a new one",
    about: "About",
    about_desc:
      "Work-hours tracking: sign in via an e-mail link, each person has their own log, Excel export and import.",
    about_contact: "Contact",
    about_close: "Close",
    lic_gate_title: "Access code",
    lic_gate_hint: "Enter the access code you were given.",
    lic_redeem: "Activate",
    lic_activated: "Access activated",
    lic_err_unknown_code: "Code not found",
    lic_err_revoked_code: "Code is disabled",
    lic_err_expired_code: "The code has expired",
    lic_err_seats_full: "This code's user limit is reached",
    lic_need_active: "An active access code is required",
    lic_banner_expired: "Access expired on {date}. Adding entries is off — renew the code.",
    lic_banner_revoked: "Access code is disabled. Contact the administrator:",
    lic_banner_trial: "Trial period until {date}.",
    lic_banner_soon: "Access valid until {date}.",
    lic_tos_label: "I accept the",
    lic_tos_link: "terms of use",
    lic_tos_required: "Please accept the terms of use",
    about_terms: "Terms of use",
    about_price: "{price}/mo per company · 14 days free · renews automatically, cancel any time",
  },
};

const CONTACT_EMAIL = "trafficit365@gmail.com";
let licenseState = null;

const SUPPORTED = ["ru", "uk", "sk", "en"];

function detectLang() {
  try {
    const saved = localStorage.getItem("chasy_lang");
    if (saved && SUPPORTED.includes(saved)) return saved;
  } catch (_) {}
  const cands = [navigator.language, ...(navigator.languages || [])];
  for (const c of cands) {
    const code = String(c || "").toLowerCase().slice(0, 2);
    if (SUPPORTED.includes(code)) return code;
  }
  return "ru";
}

let lang = detectLang();

function t(key, vars) {
  let s = (I18N[lang] && I18N[lang][key]) || I18N.ru[key] || key;
  if (vars) for (const k in vars) s = s.split(`{${k}}`).join(vars[k]);
  return s;
}

function applyI18n() {
  document.documentElement.lang = lang;
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = t(el.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-ph]").forEach((el) => {
    el.placeholder = t(el.dataset.i18nPh);
  });
  const sel = $("lang");
  if (sel) sel.value = lang;
  const ver = $("about-version");
  if (ver) ver.textContent = "v" + APP_VERSION;
  const price = $("about-price");
  if (price) price.textContent = t("about_price", { price: APP_PRICE });
  applyLicense();
}

function setLang(next) {
  if (!SUPPORTED.includes(next)) return;
  lang = next;
  try {
    localStorage.setItem("chasy_lang", next);
  } catch (_) {}
  applyI18n();
}

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

function fmtDate(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  return isNaN(d.getTime()) ? iso : d.toLocaleDateString(lang);
}

// --------------------------------------------------------------------------- //
// licensing
// --------------------------------------------------------------------------- //
function canWrite() {
  const s = licenseState && licenseState.status;
  return !s || s === "disabled" || s === "active" || s === "trial";
}

function applyLicense() {
  if (!licenseState) {
    render();
    return;
  }
  const st = licenseState;
  const gate = $("license-gate");
  const banner = $("license-banner");

  if (st.status === "none") {
    gate.hidden = false;
    $("app").hidden = true;
    return;
  }
  gate.hidden = true;
  $("app").hidden = false;

  const link = ` <a href="mailto:${CONTACT_EMAIL}">${CONTACT_EMAIL}</a>`;
  banner.hidden = true;
  banner.className = "banner";
  banner.textContent = "";
  if (st.status === "expired") {
    banner.className = "banner warn";
    banner.innerHTML =
      t("lic_banner_expired", { date: fmtDate(st.valid_until) }) + link;
    banner.hidden = false;
  } else if (st.status === "revoked") {
    banner.className = "banner warn";
    banner.innerHTML = t("lic_banner_revoked") + link;
    banner.hidden = false;
  } else if (st.status === "trial") {
    banner.textContent = t("lic_banner_trial", { date: fmtDate(st.trial_until) });
    banner.hidden = false;
  } else if (st.status === "active" && st.valid_until) {
    const daysLeft = (new Date(st.valid_until).getTime() - Date.now()) / 86400000;
    if (daysLeft <= 7) {
      banner.textContent = t("lic_banner_soon", { date: fmtDate(st.valid_until) });
      banner.hidden = false;
    }
  }
  render();
}

async function refreshLicense() {
  const r = await api("/api/me");
  if (r.ok) {
    licenseState = (await r.json()).license || { status: "disabled" };
    applyLicense();
  }
}

function licBlocked(r) {
  if (r.status === 402) {
    toast(t("lic_need_active"));
    refreshLicense();
    return true;
  }
  return false;
}

async function redeemCode(ev) {
  ev.preventDefault();
  const code = $("license-code").value.trim();
  if (!code) return;
  if (!$("license-tos").checked) return toast(t("lic_tos_required"));
  const r = await api("/api/license/redeem", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code, accept_terms: true }),
  });
  if (!r.ok) {
    let key = "err_generic";
    try {
      const map = {
        unknown_code: "lic_err_unknown_code",
        revoked_code: "lic_err_revoked_code",
        expired_code: "lic_err_expired_code",
        seats_full: "lic_err_seats_full",
        terms_not_accepted: "lic_tos_required",
      };
      key = map[(await r.json()).detail] || "err_generic";
    } catch (_) {}
    return toast(t(key));
  }
  licenseState = (await r.json()).license;
  $("license-code").value = "";
  toast(t("lic_activated"));
  applyLicense();
  await load();
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

    const isHoliday = e.date.includes("(Holiday)");
    const dateDisp = isHoliday
      ? e.date.replace(/\s*\(Holiday\)\s*/, "") + ` · ${t("holiday_tag")}`
      : e.date;

    const main = document.createElement("div");
    main.className = "main";
    main.textContent = isHoliday
      ? dateDisp
      : `${dateDisp}   ${e.start}–${e.end} → ${e.duration}`;

    const sub = document.createElement("div");
    sub.className = "sub";
    const bits = [];
    if (lunchShown && e.lunch) bits.push(`${t("lunch_label")} ${e.lunch}`);
    if (lunchShown) bits.push(`${t("net_label")} ${e.net}`);
    if (e.comment) bits.push(`✎ ${e.comment}`);
    sub.textContent = bits.join("   ·   ");

    li.append(main, sub);
    li.addEventListener("click", () => selectEntry(e.id));
    li.addEventListener("dblclick", (ev) => {
      // Double-click only selects — it must not copy the row back into the add form.
      ev.preventDefault();
      selectEntry(e.id, { keepSelection: true });
    });
    list.append(li);
  }

  $("empty").hidden = entries.length > 0;

  const total = entries.reduce((s, e) => s + minutes(e.net), 0);
  $("total").textContent = t("total", {
    h: Math.floor(total / 60),
    m: total % 60,
  });

  const idx = entries.findIndex((e) => e.id === selectedId);
  const has = idx >= 0;
  const w = canWrite();
  $("up").disabled = !w || !has || idx === 0;
  $("down").disabled = !w || !has || idx === entries.length - 1;
  $("edit").disabled = !w || !has;
  $("del").disabled = !w || !has;
  $("add").disabled = !w;
  $("holiday").disabled = !w;
  $("import-btn").disabled = !w;
  $("save-edit").disabled = !w;
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

function selectEntry(id, { keepSelection = false } = {}) {
  // Saved rows are only loaded into the form via «Изменить». A second tap
  // must not copy the row back into the add form (that created duplicates).
  if (editingId === id) {
    selectedId = id;
    render();
    return;
  }
  if (editingId) stopEdit();
  if (keepSelection) selectedId = id;
  else selectedId = selectedId === id ? null : id;
  render();
}

function sameSlot(a, b) {
  return a.date === b.date && a.start === b.start && a.end === b.end;
}

async function addEntry() {
  if (editingId || addBusy || !canWrite()) return;
  const body = formPayload();
  if (!body.date) return toast(t("err_no_date"));
  const dup = entries.find((e) => sameSlot(e, body));
  if (dup) {
    toast(t("err_dup"));
    selectedId = dup.id;
    render();
    return;
  }
  addBusy = true;
  $("add").disabled = true;
  try {
    const r = await api("/api/entries", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (licBlocked(r)) return;
    if (!r.ok) return toast((await r.json()).detail || t("err_generic"));
    clearForm();
    await load();
  } finally {
    addBusy = false;
    render();
  }
}

async function addHoliday() {
  if (!canWrite()) return;
  const iso = $("f-date").value;
  const base = iso ? isoToDots(iso) : isoToDots(new Date().toISOString().slice(0, 10));
  const r = await api("/api/entries", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ date: `${base} (Holiday)` }),
  });
  if (licBlocked(r)) return;
  if (!r.ok) return toast(t("err_generic"));
  await load();
}

function startEdit() {
  if (!canWrite()) return;
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
  if (!canWrite()) return;
  const body = formPayload();
  if (!body.date) return toast(t("err_no_date"));
  const r = await api(`/api/entries/${editingId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (licBlocked(r)) return;
  if (!r.ok) return toast((await r.json()).detail || t("err_generic"));
  stopEdit();
  await load();
}

async function del() {
  if (!selectedId || !canWrite()) return;
  const r = await api(`/api/entries/${selectedId}`, { method: "DELETE" });
  if (licBlocked(r)) return;
  if (!r.ok && r.status !== 204) return toast(t("err_generic"));
  selectedId = null;
  await load();
}

async function move(dir) {
  if (!canWrite()) return;
  const idx = entries.findIndex((e) => e.id === selectedId);
  const j = idx + dir;
  if (idx < 0 || j < 0 || j >= entries.length) return;
  [entries[idx], entries[j]] = [entries[j], entries[idx]];
  render();
  const r = await api("/api/entries/reorder", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ids: entries.map((e) => e.id) }),
  });
  if (licBlocked(r)) await load();
}

async function importFile(file) {
  if (!canWrite()) return;
  const fd = new FormData();
  fd.append("file", file);
  const r = await api("/api/import", { method: "POST", body: fd });
  if (licBlocked(r)) return;
  if (!r.ok) return toast((await r.json()).detail || t("err_import"));
  const { imported } = await r.json();
  toast(t("imported", { n: imported }));
  await load();
}

// --------------------------------------------------------------------------- //
// auth views
// --------------------------------------------------------------------------- //
function showLogin() {
  $("app").hidden = true;
  $("license-gate").hidden = true;
  $("login").hidden = false;
  $("who").hidden = true;
  $("logout").hidden = true;
}

async function showApp(me) {
  $("login").hidden = true;
  $("who").textContent = me.email;
  $("who").hidden = false;
  $("logout").hidden = false;
  licenseState = me.license || { status: "disabled" };
  applyLicense();
  if (licenseState.status !== "none") await load();
}

// --------------------------------------------------------------------------- //
// wire up
// --------------------------------------------------------------------------- //
$("lang").addEventListener("change", (ev) => setLang(ev.target.value));

$("license-form").addEventListener("submit", redeemCode);

$("about-btn").addEventListener("click", () => {
  const dlg = $("about");
  if (typeof dlg.showModal === "function") dlg.showModal();
  else dlg.setAttribute("open", "");
});

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
  else toast(t("err_mail"));
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
  applyI18n();

  const params = new URLSearchParams(location.search);
  if (params.get("error") === "link") {
    toast(t("err_link"));
    history.replaceState({}, "", "/");
  }
  const r = await api("/api/me");
  if (r.ok) {
    showApp(await r.json());
  } else {
    showLogin();
  }
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js").catch(() => {});
  }
})();
