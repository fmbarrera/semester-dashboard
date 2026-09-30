// Semester Dashboard — list and calendar views. Plain JS, no build step.
// Fetches everything once (a semester is ~100 items), filters client-side,
// and patches single items in place when they change.

const GROUPS = [
  ["overdue", "Overdue"],
  ["due_soon", "Due in the next 2 days"],
  ["this_week", "This week"],
  ["later", "Later"],
  ["no_date", "Date not published yet"],
];
const PALETTE_SIZE = 8;

const VIEWS = ["open", "completed", "calendar"];
const HEAVY_DAY_HOURS = 6;
const MAX_PILLS = 3;

const state = {
  view: "open", // one of VIEWS
  course: null, // course id, or null for all
  courses: [],
  assignments: [],
  collapsed: new Set(),
  cal: null, // { year, month } shown in the calendar; set in init()
  selected: null, // ISO date picked in the calendar, or null
};

const $ = (sel) => document.querySelector(sel);

// ---------- persistence of per-browser UI prefs ----------

function loadPrefs() {
  try {
    const p = JSON.parse(localStorage.getItem("dashboard-prefs") || "{}");
    if (VIEWS.includes(p.view)) state.view = p.view;
    if (typeof p.course === "string") state.course = p.course;
    if (Array.isArray(p.collapsed)) state.collapsed = new Set(p.collapsed);
  } catch {}
}

function savePrefs() {
  try {
    localStorage.setItem(
      "dashboard-prefs",
      JSON.stringify({ view: state.view, course: state.course, collapsed: [...state.collapsed] }),
    );
  } catch {}
}

// ---------- API ----------

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {}
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return res.json();
}

async function patchAssignment(id, body) {
  const updated = await api(`/api/assignments/${encodeURIComponent(id)}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
  const i = state.assignments.findIndex((a) => a.id === id);
  state.assignments[i] = updated;
  render();
}

// ---------- formatting ----------

const esc = (s) =>
  String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

// "2026-10-07" -> local-midnight Date (new Date("2026-10-07") would be UTC).
function parseDate(iso) {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d);
}

// Local Date -> "2026-10-07" (toISOString() would shift to UTC).
const toISO = (d) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

const fmtDate = (iso) =>
  parseDate(iso).toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" });

function fmtTime(t) {
  const [h, m] = t.split(":").map(Number);
  return new Date(2000, 0, 1, h, m).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
}

function fmtRelative(days) {
  if (days === 0) return "today";
  if (days === 1) return "tomorrow";
  if (days === -1) return "1 day overdue";
  if (days < 0) return `${-days} days overdue`;
  return `in ${days} days`;
}

function fmtWeight(a) {
  if (a.weight_value == null) return null;
  const v = +a.weight_value.toFixed(2);
  return a.weight_unit === "points" ? `${v} pts` : `${v}%`;
}

const fmtHours = (h) => `${+h.toFixed(2)}h`;
const sumHours = (items) => items.reduce((t, a) => t + a.estimate.hours, 0);

function courseColor(courseId) {
  const i = state.courses.findIndex((c) => c.id === courseId);
  return `var(--c${i % PALETTE_SIZE})`;
}

// ---------- rendering ----------

function renderStats() {
  const open = state.assignments.filter((a) => a.status !== "completed");
  const week = open.filter((a) => ["due_soon", "this_week"].includes(a.urgency));
  const overdue = open.filter((a) => a.urgency === "overdue");
  $("#stats").innerHTML = `
    <div><dt>Next 7 days</dt><dd>${week.length} · ${fmtHours(sumHours(week))}</dd></div>
    <div><dt>Overdue</dt><dd class="${overdue.length ? "danger" : ""}">${overdue.length}</dd></div>
  `;
}

function renderFilters() {
  for (const btn of document.querySelectorAll(".tabs button")) {
    btn.setAttribute("aria-selected", String(btn.dataset.view === state.view));
  }
  // The calendar shows everything, but its chips count what's still open.
  const inView = (a) => (state.view === "completed") === (a.status === "completed");
  const count = (id) => state.assignments.filter((a) => inView(a) && (id == null || a.course_id === id)).length;

  const chip = (id, label, color) => `
    <button class="chip" data-course="${id ?? ""}" aria-pressed="${state.course === id}"
            ${color ? `style="--course:${color}"` : ""}>
      ${color ? '<span class="dot"></span>' : ""}${esc(label)}
      <span class="count">${count(id)}</span>
    </button>`;
  $("#course-filter").innerHTML =
    chip(null, "All classes") +
    state.courses.map((c) => chip(c.id, c.code, courseColor(c.id))).join("");
}

function renderItem(a) {
  const done = a.status === "completed";
  const parts = [];
  if (a.due_date) {
    const when = a.due_time ? `${fmtDate(a.due_date)}, ${fmtTime(a.due_time)}` : fmtDate(a.due_date);
    parts.push(a.date_tbd ? `~${when} (approx.)` : when);
    if (!done) parts.push(`<span class="rel ${a.urgency}">${fmtRelative(a.days_until)}</span>`);
  } else {
    parts.push("No date yet");
  }
  const weight = fmtWeight(a);
  if (weight) parts.push(`<span class="weight">${weight}</span>`);
  if (done) parts.push(`done ${new Date(a.completed_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })}`);

  const est = a.estimate;
  const hoursTitle =
    est.source === "user_override"
      ? `Your estimate (default for ${a.category.replace("_", " ")}: ${fmtHours(est.default_hours)}). Click to change.`
      : `Default estimate for ${a.category.replace("_", " ")}. Click to change.`;

  return `
    <li class="item ${done ? "is-done" : ""}" data-id="${esc(a.id)}" style="--course:${courseColor(a.course_id)}">
      <input type="checkbox" class="check" ${done ? "checked" : ""}
             aria-label="Mark “${esc(a.title)}” ${done ? "not complete" : "complete"}">
      <div>
        <div class="line1">
          <span class="course">${esc(a.course_code)}</span>
          <span class="title">${esc(a.title)}</span>
          ${a.date_tbd ? '<span class="tag tbd">TBD</span>' : ""}
          ${a.is_team ? '<span class="tag">Team</span>' : ""}
        </div>
        <div class="meta">${parts.join(" · ")}</div>
        ${a.notes ? `<details class="notes"><summary>Notes</summary><p>${esc(a.notes)}</p></details>` : ""}
      </div>
      <button class="hours ${est.source === "user_override" ? "overridden" : ""}" title="${esc(hoursTitle)}">
        ${fmtHours(est.hours)}
      </button>
    </li>`;
}

function renderGroup(key, label, items) {
  const open = !state.collapsed.has(key);
  const summary =
    key === "completed"
      ? `${items.length}`
      : `${items.length} ${items.length === 1 ? "item" : "items"} · ${fmtHours(sumHours(items))}`;
  return `
    <details class="group ${key}" data-group="${key}" ${open ? "open" : ""}>
      <summary><h2>${label}</h2><span class="summary">${summary}</span></summary>
      <ul class="items">${items.map(renderItem).join("")}</ul>
    </details>`;
}

function renderList() {
  const forCourse = state.assignments.filter((a) => state.course == null || a.course_id === state.course);
  if (state.view === "calendar") {
    renderCalendar(forCourse);
    return;
  }
  const items = forCourse.filter((a) => (state.view === "completed") === (a.status === "completed"));

  if (!items.length) {
    $("#list").innerHTML = `<p class="empty">${
      state.view === "completed" ? "Nothing completed yet." : "Nothing left to do here."
    }</p>`;
    return;
  }

  if (state.view === "completed") {
    items.sort((a, b) => b.completed_at.localeCompare(a.completed_at));
    $("#list").innerHTML = renderGroup("completed", "Completed", items);
    return;
  }

  // Server already returns items in due-date order; just bucket them.
  $("#list").innerHTML = GROUPS.map(([key, label]) => {
    const group = items.filter((a) => a.urgency === key);
    return group.length ? renderGroup(key, label, group) : "";
  }).join("");
}

// ---------- calendar ----------

function renderCalendar(items) {
  const { year, month } = state.cal;
  const first = new Date(year, month, 1);
  const last = new Date(year, month + 1, 0);
  // Full weeks, Sunday through Saturday.
  const start = new Date(year, month, 1 - first.getDay());
  const end = new Date(year, month, last.getDate() + (6 - last.getDay()));
  const todayISO = toISO(new Date());

  const byDate = new Map();
  for (const a of items) {
    if (!a.due_date) continue;
    if (!byDate.has(a.due_date)) byDate.set(a.due_date, []);
    byDate.get(a.due_date).push(a);
  }

  const weekdays = [];
  for (let i = 0; i < 7; i++) {
    const d = new Date(start);
    d.setDate(start.getDate() + i);
    weekdays.push(`<div class="weekday">${d.toLocaleDateString(undefined, { weekday: "short" })}</div>`);
  }

  const cells = [];
  for (const d = new Date(start); d <= end; d.setDate(d.getDate() + 1)) {
    const iso = toISO(d);
    const dayItems = byDate.get(iso) ?? [];
    const open = dayItems.filter((a) => a.status !== "completed");
    const hours = sumHours(open);
    // All pills are rendered; CSS hides the extras on desktop (phones show dots for all).
    const pills = dayItems
      .map(
        (a, i) => `<span class="pill ${a.status === "completed" ? "done" : ""} ${a.date_tbd ? "tbd" : ""} ${
          i >= MAX_PILLS ? "extra" : ""
        }"
                      style="--course:${courseColor(a.course_id)}" title="${esc(`${a.course_code}: ${a.title}`)}">
                  <span class="pill-text">${a.date_tbd ? "~" : ""}${esc(a.title)}</span></span>`,
      )
      .join("");
    const more = dayItems.length > MAX_PILLS ? `<span class="more">+${dayItems.length - MAX_PILLS} more</span>` : "";
    const label = `${fmtDate(iso)}: ${dayItems.length} ${dayItems.length === 1 ? "item" : "items"}${
      hours ? `, ${fmtHours(hours)} open` : ""
    }`;
    const classes = [
      "day",
      d.getMonth() !== month && "other-month",
      iso === todayISO && "today",
      iso === state.selected && "selected",
    ].filter(Boolean);
    cells.push(`
      <button class="${classes.join(" ")}" data-date="${iso}" aria-label="${esc(label)}"
              aria-pressed="${iso === state.selected}">
        <span class="day-head">
          <span class="num">${d.getDate()}</span>
          ${hours ? `<span class="load ${hours >= HEAVY_DAY_HOURS ? "heavy" : ""}">${fmtHours(hours)}</span>` : ""}
        </span>
        <span class="pills">${pills}${more}</span>
      </button>`);
  }

  const undated = items.filter((a) => !a.due_date && a.status !== "completed").length;
  const monthName = first.toLocaleDateString(undefined, { month: "long", year: "numeric" });

  $("#list").innerHTML = `
    <div class="cal-head">
      <h2>${monthName}</h2>
      <div class="cal-nav">
        <button data-cal="prev" aria-label="Previous month">‹</button>
        <button data-cal="today">Today</button>
        <button data-cal="next" aria-label="Next month">›</button>
      </div>
    </div>
    <div class="cal-grid">${weekdays.join("")}${cells.join("")}</div>
    ${
      undated
        ? `<p class="cal-note">${undated} open ${undated === 1 ? "item has" : "items have"} no date yet —
             <button class="link" data-goto="open">see Upcoming</button>.</p>`
        : ""
    }
    <section class="day-detail">${renderDayDetail(byDate)}</section>`;
}

function renderDayDetail(byDate) {
  if (!state.selected) return `<p class="empty">Pick a day to see what's due.</p>`;
  const items = byDate.get(state.selected) ?? [];
  const title = parseDate(state.selected).toLocaleDateString(undefined, {
    weekday: "long",
    month: "long",
    day: "numeric",
  });
  const open = items.filter((a) => a.status !== "completed");
  const summary = items.length
    ? `${items.length} ${items.length === 1 ? "item" : "items"}${open.length ? ` · ${fmtHours(sumHours(open))} open` : ""}`
    : "";
  return `
    <div class="day-detail-head"><h2>${title}</h2><span class="summary">${summary}</span></div>
    ${items.length ? `<ul class="items">${items.map(renderItem).join("")}</ul>` : `<p class="empty">Nothing due.</p>`}`;
}

function showMonth(year, month) {
  const d = new Date(year, month, 1); // normalizes month -1 / 12
  state.cal = { year: d.getFullYear(), month: d.getMonth() };
}

function render() {
  // Mirror the view in the URL so it can be bookmarked (e.g. /#calendar).
  history.replaceState(null, "", state.view === "open" ? location.pathname : `#${state.view}`);
  renderStats();
  renderFilters();
  renderList();
}

// ---------- interactions ----------

function toast(message) {
  const el = $("#toast");
  el.textContent = message;
  el.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => (el.hidden = true), 4000);
}

function editHours(button) {
  const id = button.closest(".item").dataset.id;
  const a = state.assignments.find((x) => x.id === id);
  const input = document.createElement("input");
  input.type = "number";
  input.min = "0.25";
  input.step = "0.25";
  input.className = "hours-input";
  input.value = a.estimate.hours;
  input.title = `Hours. Leave empty to reset to the default (${fmtHours(a.estimate.default_hours)}).`;
  button.replaceWith(input);
  input.focus();
  input.select();

  let finished = false;
  const finish = async (save) => {
    if (finished) return;
    finished = true;
    const raw = input.value.trim();
    const value = raw === "" ? null : Number(raw);
    if (!save || value === a.estimate.hours || (value === null && a.estimate.override_hours === null)) {
      render();
      return;
    }
    if (value !== null && !(value > 0)) {
      toast("Hours must be a positive number.");
      render();
      return;
    }
    try {
      await patchAssignment(id, { override_hours: value });
    } catch (err) {
      toast(`Couldn't save estimate: ${err.message}`);
      render();
    }
  };
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") finish(true);
    if (e.key === "Escape") finish(false);
  });
  input.addEventListener("blur", () => finish(true));
}

function bindEvents() {
  $(".tabs").addEventListener("click", (e) => {
    const btn = e.target.closest("button[data-view]");
    if (!btn) return;
    state.view = btn.dataset.view;
    savePrefs();
    render();
  });

  $("#course-filter").addEventListener("click", (e) => {
    const chip = e.target.closest(".chip");
    if (!chip) return;
    state.course = chip.dataset.course || null;
    savePrefs();
    render();
  });

  $("#list").addEventListener("change", async (e) => {
    if (!e.target.matches(".check")) return;
    const id = e.target.closest(".item").dataset.id;
    try {
      await patchAssignment(id, { completed: e.target.checked });
    } catch (err) {
      e.target.checked = !e.target.checked;
      toast(`Couldn't update: ${err.message}`);
    }
  });

  $("#list").addEventListener("click", (e) => {
    const hours = e.target.closest(".hours");
    if (hours) return editHours(hours);

    const nav = e.target.closest("[data-cal]");
    if (nav) {
      const { year, month } = state.cal;
      if (nav.dataset.cal === "prev") showMonth(year, month - 1);
      if (nav.dataset.cal === "next") showMonth(year, month + 1);
      if (nav.dataset.cal === "today") {
        const now = new Date();
        showMonth(now.getFullYear(), now.getMonth());
        state.selected = toISO(now);
      }
      return render();
    }

    const day = e.target.closest(".day");
    if (day) {
      state.selected = day.dataset.date;
      const d = parseDate(day.dataset.date);
      if (d.getMonth() !== state.cal.month) showMonth(d.getFullYear(), d.getMonth());
      render();
      document.querySelector(".day-detail")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
      return;
    }

    const goto = e.target.closest("[data-goto]");
    if (goto) {
      state.view = goto.dataset.goto;
      savePrefs();
      render();
    }
  });

  // <details> toggle events don't bubble, so listen in the capture phase.
  $("#list").addEventListener(
    "toggle",
    (e) => {
      const key = e.target.dataset?.group;
      if (!key) return;
      e.target.open ? state.collapsed.delete(key) : state.collapsed.add(key);
      savePrefs();
    },
    true,
  );
}

async function init() {
  loadPrefs();
  const fromHash = location.hash.slice(1);
  if (VIEWS.includes(fromHash)) state.view = fromHash;
  const now = new Date();
  showMonth(now.getFullYear(), now.getMonth());
  state.selected = toISO(now);
  bindEvents();
  $("#today").textContent = new Date().toLocaleDateString(undefined, {
    weekday: "long",
    month: "long",
    day: "numeric",
  });
  try {
    const [courses, assignments] = await Promise.all([api("/api/courses"), api("/api/assignments")]);
    state.courses = courses;
    state.assignments = assignments;
    if (state.course && !courses.some((c) => c.id === state.course)) state.course = null;
    render();
  } catch (err) {
    $("#list").innerHTML = `<p class="empty">Couldn't load assignments: ${esc(err.message)}</p>`;
  }
}

init();
