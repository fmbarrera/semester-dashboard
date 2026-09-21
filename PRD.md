# Semester Dashboard — Product Requirements Document

**Status:** Draft v0.1 — for review
**Owner:** Federico Morales Barrera
**Last updated:** 2026-09-12

## 1. Problem

Fall 2026 spans 7 classes, each with its own syllabus, grading scheme, and
assignment cadence, scattered across PDFs, a Word doc, and Canvas screenshots.
There's no single place that answers "what's due this week, how much is it
worth, and how long will it take me?" Missing a graded deadline — or
under-preparing for one because it snuck up — carries real GPA risk.

## 2. Goals

- One view that answers "what's coming up, across all classes, ranked by
  urgency and grade weight."
- Track completion status per assignment (done / not done).
- Attach a time-investment estimate to each assignment so planning is
  concrete ("this needs 1.5h of studying," not just "due Friday").
- Ship as a real, working local web app — usable daily, not just a demo.
- Be presentable on GitHub as a portfolio piece: clean structure, tests,
  a README that explains the "why," and no exposed personal data.

## 3. Non-goals (v1)

- Not a full LMS replacement — no submitting actual coursework, no file
  storage for deliverables.
- Not multi-user / no auth system — this is a personal tool for one student.
- Not syncing to Canvas, Google Calendar, or any external calendar (could be
  a future integration, not v1).
- Not auto-parsing syllabi with AI at runtime — the assignment data is
  curated once (by this project's setup process) and stored locally; the
  app itself just reads/writes that data.
- Auto-spacing a project into daily study blocks is **Phase 2**, not v1
  (see §7).

## 4. User

Single user: a part-time MBA student carrying 7 classes with very different
grading philosophies (points-based ungrading, weighted percentages, relative
curves). They're comfortable in Python and want to actually use this tool
every week, not just build it once and abandon it.

## 5. Core user stories (v1)

1. As the user, I open the dashboard and immediately see the next 7–14 days
   of graded deadlines across all classes, sorted by due date.
2. As the user, I can see, for any assignment, which class it belongs to,
   its grade weight/points, and an estimated time investment.
3. As the user, I can mark an assignment complete, and it drops out of the
   "upcoming" view but remains visible in a history/completed view.
4. As the user, I can view assignments on a calendar (month/week grid), not
   just a flat list.
5. As the user, when a professor hasn't published a due date yet, I still
   see the assignment (flagged "TBD") instead of it silently missing.
6. As the user, I can override the default time estimate for any single
   assignment (e.g., "this quiz will actually take me 3 hours, not 1.5").
7. As the user, I can filter/view by class.

## 6. MVP feature set

- **Data layer:** SQLite database (`data/dashboard.db`, gitignored — real
  personal data never committed). Seeded from a version-controlled
  `seed/courses.yaml` (structure + rules) and a gitignored
  `seed/assignments.local.yaml` (actual Fall 2026 deadlines). A
  `seed/assignments.sample.yaml` with fictional demo data ships in the repo
  so anyone cloning it sees a working app immediately.
- **Backend:** FastAPI app exposing a small REST API (list assignments,
  get one, update completion state, override time estimate, list courses).
- **Frontend:** single-page vanilla HTML/CSS/JS dashboard served by
  FastAPI (Jinja2 templates + static JS/CSS, no build step, no framework).
  Two views: **List/Dashboard** (upcoming, grouped by urgency) and
  **Calendar** (month grid with color-coding by class).
- **Time estimates:** a small rules table by assignment type (quiz, exam,
  paper, project, case, presentation, recurring homework, etc.) with a
  default hours value; each assignment can override it individually.
- **Network access:** runs via `python app.py` (uvicorn under the hood),
  bound to `0.0.0.0`, so it's reachable from a phone on the same wifi at
  `http://<mac-lan-ip>:8000`.
- **Tests:** pytest coverage for the API layer and the time-estimate/urgency
  logic.

## 7. Phase 2 (post-MVP)

- Auto-spacing: a project/paper with a "spread over N days" estimate gets
  broken into daily sub-tasks (e.g., 1h/day for 10 days) that show up on
  the calendar individually and can each be checked off.
- Weekly digest / notification (e.g., a Sunday-night summary).
- Google Calendar export (read-only `.ics` feed).
- Basic analytics: hours planned vs. hours actually logged, grade-weight
  coverage per week (are heavy weeks visible in advance?).

## 8. Data model (v1)

```
Course
  id, code (e.g. "ACT538"), name, professor, weight_scheme (points | percent)

Assignment
  id, course_id, title, category (quiz | exam | project | paper | case |
    presentation | homework | participation | other),
  due_date (nullable -> TBD), due_time (nullable),
  weight_value (points or percent, per course's weight_scheme),
  weight_label (free text, e.g. "20% of final grade" or "120 pts"),
  is_team (bool), status (upcoming | completed | tbd),
  notes (free text, e.g. reconciliation notes on ambiguous source data)

TimeEstimate
  assignment_id (1:1), category_default_hours (from rule table),
  override_hours (nullable), source (default | user_override)

EstimateRule
  category, default_hours   # editable in one config file
```

## 9. Tech stack

- Python 3.12, FastAPI, Uvicorn, SQLModel (SQLAlchemy + Pydantic) for the
  ORM/schema layer, Alembic optional (v1 can just recreate the DB from seed
  since it's single-user).
- Frontend: plain HTML/CSS/JS, `fetch()` against the FastAPI JSON API.
  FullCalendar (via CDN) or a small hand-rolled month grid — TBD during
  implementation, evaluated for simplicity.
- pytest + httpx for API tests.
- No cloud dependency — everything runs locally.

## 10. Privacy / GitHub hygiene

- `.gitignore`: `data/dashboard.db`, `seed/assignments.local.yaml`, any
  `.env`.
- Repo ships with `seed/assignments.sample.yaml` (fictional courses/dates)
  so `git clone` → `python app.py` produces a working demo.
- README documents how to drop in your own `assignments.local.yaml` to use
  it for real.

## 11. Success metrics (informal, personal project)

- Used at least weekly through the semester without needing to re-check a
  syllabus PDF for a graded date.
- Zero missed graded deadlines that were already in the source syllabi.
- Repo is clean enough to link from a resume/portfolio without editing.

## 12. Open questions / risks

- FullCalendar (JS lib) vs. hand-rolled calendar grid — decide during
  frontend implementation; leaning hand-rolled to avoid an external JS
  dependency for something this small.
- EPE and Blockchain have TBD items (exact dates unknown) — these will
  need manual updates once the professor publishes them; the data model
  supports `due_date = null` + `status = tbd` for this.
- Doing Deals final exam date is officially TBD from the syllabus itself.

## 13. Milestones

1. **Repo scaffold + PRD (this doc)** — done
2. **Data model + seed files** (sample + real, both course sets fully
   transcribed from syllabi)
3. **FastAPI backend + tests** (CRUD on assignments, completion toggling,
   time estimate overrides)
4. **Frontend v1** (list/dashboard view)
5. **Frontend v1** (calendar view)
6. **README + GitHub polish**
7. **Phase 2: auto-spacing scheduler**
