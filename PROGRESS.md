# Progress Log / Resume Point

**Last session:** 2026-09-29
**Repo:** https://github.com/fmbarrera/semester-dashboard

## Where things stand

Milestones 1–4 from `PRD.md` §13 are done (scaffold + PRD, seed data,
FastAPI backend + tests, list/dashboard frontend):

- [x] Git repo created at `~/Developer/semester-dashboard`, pushed to
      GitHub (public), `gh` authenticated, global git identity fixed
      (was corrupted before this project).
- [x] `PRD.md` — full product requirements doc, reviewed and accepted.
- [x] `.gitignore` covers personal data (`seed/*.local.yaml`, `data/`,
      `*.db`) and a broad set of credential/secret file patterns.
- [x] `.pre-commit-config.yaml` wires up **gitleaks** as a pre-commit
      hook — verified it actually blocks a commit containing a fake AWS
      key. Hook is installed locally (`pre-commit install` already run
      in this repo).
- [x] `seed/estimate_rules.yaml` — default time-investment hours per
      assignment category (committed, shared).
- [x] `seed/courses.sample.yaml` + `seed/assignments.sample.yaml` —
      fictional demo data (committed), so a fresh clone works out of
      the box. Sample assignments use `due_in_days` (relative offsets)
      instead of fixed dates, so the demo always looks current.
- [x] `seed/courses.local.yaml` + `seed/assignments.local.yaml` — your
      real Fall 2026 data, all 7 classes, transcribed from the syllabi.
      **Gitignored — lives only on this machine, never pushed.**
- [x] `seed/README.md` — documents the schema and the sample/local split.
- [x] **FastAPI backend** (`dashboard/`, `app.py`), 2026-09-29:
      - `models.py` — SQLModel tables `Course`, `Assignment`,
        `TimeEstimate`, `EstimateRule`. Status is *derived* (completed if
        `completed_at` set, else tbd if `date_tbd`, else upcoming), so
        un-completing never loses TBD-ness. `date_tbd` is its own flag
        because `blockchain304-project-idea-checkin` is TBD *with* an
        approximate date (10/15).
      - `seed.py` — loads local pair if both exist, else sample; validates
        everything (unknown course/category, dup ids, bad times, mixed
        date styles…) and fails loudly. **Re-seeding keeps completion
        state and estimate overrides** by assignment id.
      - `logic.py` — urgency buckets: overdue / due_soon (≤2d) /
        this_week (≤7d) / later / no_date / done; sort order.
      - `api.py` — `GET /api/courses`, `GET /api/assignments`
        (`?course_id=`, `?status=upcoming|completed|tbd|open`,
        `?within_days=N`), `GET/PATCH /api/assignments/{id}`
        (`{"completed": bool}`, `{"override_hours": float|null}`),
        `GET /api/estimate-rules`. Under `/api` so the HTML can own `/`.
      - `app.py` — `python app.py [--reseed] [--port N]`, binds 0.0.0.0.
        DB at `data/dashboard.db` (override with `DASHBOARD_DB`).
- [x] **Tests** — 40 pytest tests (`tests/`), all passing. They copy only
      the sample seed files into a tmp dir, so they never touch real data.
- [x] Smoke-tested against the real local data: all 63 assignments /
      7 courses load and validate cleanly.
- [x] **Frontend v1 — list view** (`dashboard/static/`), 2026-09-30:
      plain `index.html` + `app.js` + `style.css` served at `/` (no
      Jinja needed — the page is fully static and fetches the API, a small
      deviation from PRD §6). Groups by urgency with count + hours per
      group, checkbox to complete, click the hours to override (empty =
      reset to default), course filter chips, Upcoming/Completed tabs,
      expandable notes, TBD/Team tags, header stats (next 7 days,
      overdue). Light + dark mode; checked at 390px phone width. View,
      filter and collapsed groups remembered per browser (localStorage).

## Not started yet

- [ ] Frontend calendar view (month grid, color-coded by class).
- [ ] `README.md` for the project itself (setup instructions, screenshot,
      "how to add your own semester" section).
- [ ] Phase 2: auto-spacing scheduler for multi-day project planning.

## Open questions to resolve before/while building the backend

These are judgment calls made while transcribing `assignments.local.yaml`
that should get a second look once you can see the data rendered in the
app (easier to spot errors there than in raw YAML):

1. **MKT637** — "Data-driven analysis" (Nov 4) and "Draft final
   presentation" (Nov 17) were marked as unweighted checkpoints toward
   the 20% Final Project, since the syllabus's grade table doesn't list
   them separately. Confirm this is right.
2. **PORT110 weekly homework** — syllabus only gives "Homework 20%"
   total with no per-item breakdown; I split it evenly across ~11 items
   (1.8% each). May not match the professor's actual weighting.
3. **Blockchain (ACT 304/504)** — sparsest syllabus of the 7. Homework
   has zero published due dates; final project presentation/whitepaper
   dates are pure TBD. This class will look empty on the dashboard until
   more info shows up on Canvas — that's expected, not a bug.
4. **EPE case reports** — split the 20% "Case Reports" bucket evenly
   across the two cases (10% each); syllabus doesn't confirm they're
   weighted evenly.

## Next concrete step

1. Check off the ~10 past items that show as overdue only because they
   haven't been marked done, and walk through the four open questions above
   now that the data is visible.
2. Calendar view (PRD milestone 5): month grid, color-coded by class
   using the same `--c0..--c7` palette as the list view. Leaning
   hand-rolled over FullCalendar (PRD §12).

## How to resume

Tell Claude: *"Pick up the semester-dashboard project — check
PROGRESS.md."* Everything needed to continue is in this file plus
`PRD.md` and `seed/README.md`.

Useful commands:

```bash
cd ~/Developer/semester-dashboard
python3.12 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt  # first time
.venv/bin/python -m pytest -q    # run tests
.venv/bin/python app.py          # http://localhost:8000 (API docs at /docs)
.venv/bin/python app.py --reseed # after editing seed/*.yaml
git log --oneline          # see what's been committed
git status                 # anything in flight
gh repo view --web         # open the GitHub repo
```
