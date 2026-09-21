# Progress Log / Resume Point

**Last session:** 2026-09-20
**Repo:** https://github.com/fmbarrera/semester-dashboard

## Where things stand

Milestone 1 (repo scaffold + PRD) and most of milestone 2 (seed data) from
`PRD.md` §13 are done:

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

## Not started yet

- [ ] FastAPI backend (data models, loader that reads the seed YAML into
      SQLite, REST API for listing/completing assignments and overriding
      time estimates).
- [ ] Frontend (list/dashboard view, then calendar view).
- [ ] Tests (pytest for the API + urgency/estimate logic).
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

Build the FastAPI backend: SQLModel schema (`Course`, `Assignment`,
`TimeEstimate`), a seed-loader that reads `seed/*.yaml` (local if
present, else sample) into SQLite on first run, and a small REST API
(`GET /assignments`, `PATCH /assignments/{id}` for completion +
estimate overrides, `GET /courses`). Once that exists, the four open
questions above become much easier to check by actually looking at the
dashboard instead of raw YAML.

## How to resume

Tell Claude: *"Pick up the semester-dashboard project — check
PROGRESS.md."* Everything needed to continue is in this file plus
`PRD.md` and `seed/README.md`.

Useful commands:

```bash
cd ~/Developer/semester-dashboard
git log --oneline          # see what's been committed
git status                 # anything in flight
gh repo view --web         # open the GitHub repo
```
