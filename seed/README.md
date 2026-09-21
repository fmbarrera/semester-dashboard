# Seed data

Four files, two pairs:

| File | Committed? | Purpose |
|---|---|---|
| `courses.sample.yaml` | Yes | Fictional courses, for a fresh clone / demo |
| `assignments.sample.yaml` | Yes | Fictional assignments, uses `due_in_days` (relative) so the demo always looks current |
| `courses.local.yaml` | **No** (gitignored) | Real Fall 2026 courses |
| `assignments.local.yaml` | **No** (gitignored) | Real Fall 2026 assignments, uses absolute `due_date` |

`estimate_rules.yaml` is shared and committed — default hours per
assignment `category`, used when an assignment has no per-item time
override.

## Loader behavior

On startup, the seed loader looks for `*.local.yaml` first; if absent, it
falls back to `*.sample.yaml`. This means:

- Cloning the repo fresh → sample/demo data, works immediately.
- Dropping in your own `courses.local.yaml` + `assignments.local.yaml`
  (same schema) → your real data, never committed.

## Assignment schema

```yaml
id: unique-slug              # required, unique across the whole file
course_id: some-course-id    # must match a course id in the paired courses file
title: "Display name"        # required
category: quiz               # quiz | exam | project | paper | case |
                              # presentation | homework | problem_set |
                              # discussion_post | reflection | other
due_date: 2026-10-07          # YYYY-MM-DD, or null if unpublished
due_in_days: 5                 # sample data only: int, relative to seed-run time
due_time: "23:59"             # 24h "HH:MM", or null
weight_value: 20               # number, or null if not separately graded
weight_unit: percent           # points | percent | null
is_team: false
status: tbd                    # omit for normal items; "tbd" pairs with a null date
notes: "free text"             # provenance, caveats, ambiguity notes
```

Real data uses `due_date`; sample data uses `due_in_days` instead. A file
should use one or the other consistently, not mix them.
