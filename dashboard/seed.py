"""Load seed/*.yaml into the database.

Picks the *.local.yaml pair when both files exist, else the committed
*.sample.yaml pair (see seed/README.md). Validates everything up front and
raises SeedError with a readable message rather than half-loading bad data:
a silently skipped assignment is a missed deadline.
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path

import yaml
from sqlmodel import Session, select

from .models import (
    CATEGORIES,
    WEIGHT_SCHEMES,
    WEIGHT_UNITS,
    Assignment,
    Course,
    EstimateRule,
    TimeEstimate,
)


class SeedError(ValueError):
    pass


@dataclass(frozen=True)
class SeedFiles:
    courses: Path
    assignments: Path
    rules: Path
    kind: str  # "local" | "sample"


def find_seed_files(seed_dir: Path) -> SeedFiles:
    local_c = seed_dir / "courses.local.yaml"
    local_a = seed_dir / "assignments.local.yaml"
    rules = seed_dir / "estimate_rules.yaml"
    if local_c.exists() != local_a.exists():
        present = local_c if local_c.exists() else local_a
        raise SeedError(
            f"Found {present.name} but not its pair — local data needs both "
            "courses.local.yaml and assignments.local.yaml."
        )
    if local_c.exists():
        return SeedFiles(local_c, local_a, rules, "local")
    return SeedFiles(
        seed_dir / "courses.sample.yaml",
        seed_dir / "assignments.sample.yaml",
        rules,
        "sample",
    )


def _read_yaml(path: Path) -> dict:
    try:
        with path.open() as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        raise SeedError(f"Seed file not found: {path}") from None
    if not isinstance(data, dict):
        raise SeedError(f"{path.name}: expected a mapping at the top level")
    return data


def _parse_time(value, where: str) -> time | None:
    if value is None:
        return None
    try:
        return datetime.strptime(str(value), "%H:%M").time()
    except ValueError:
        raise SeedError(f'{where}: due_time must be "HH:MM", got {value!r}') from None


def _parse_rules(data: dict) -> dict[str, float]:
    rules = data.get("categories")
    if not isinstance(rules, dict):
        raise SeedError("estimate_rules.yaml: missing 'categories' mapping")
    missing = set(CATEGORIES) - rules.keys()
    if missing:
        raise SeedError(f"estimate_rules.yaml: no default hours for {sorted(missing)}")
    return {k: float(v) for k, v in rules.items()}


def _parse_courses(data: dict) -> list[Course]:
    courses = []
    seen = set()
    for raw in data.get("courses") or []:
        cid = raw.get("id")
        where = f"course {cid!r}"
        if not cid:
            raise SeedError("A course is missing its 'id'")
        if cid in seen:
            raise SeedError(f"{where}: duplicate id")
        seen.add(cid)
        if raw.get("weight_scheme") not in WEIGHT_SCHEMES:
            raise SeedError(f"{where}: weight_scheme must be one of {WEIGHT_SCHEMES}")
        courses.append(
            Course(
                id=cid,
                code=raw["code"],
                name=raw["name"],
                professor=raw.get("professor"),
                weight_scheme=raw["weight_scheme"],
                total_points=raw.get("total_points"),
                schedule=raw.get("schedule"),
                notes=(raw.get("notes") or "").strip() or None,
            )
        )
    return courses


def _parse_assignments(
    data: dict, course_ids: set[str], today: date
) -> list[Assignment]:
    items = data.get("assignments") or []
    uses_absolute = any("due_date" in raw for raw in items)
    uses_relative = any("due_in_days" in raw for raw in items)
    if uses_absolute and uses_relative:
        raise SeedError(
            "assignments file mixes due_date and due_in_days — use one consistently"
        )

    assignments = []
    seen = set()
    for raw in items:
        aid = raw.get("id")
        where = f"assignment {aid!r}"
        if not aid:
            raise SeedError("An assignment is missing its 'id'")
        if aid in seen:
            raise SeedError(f"{where}: duplicate id")
        seen.add(aid)
        if raw.get("course_id") not in course_ids:
            raise SeedError(f"{where}: unknown course_id {raw.get('course_id')!r}")
        if raw.get("category") not in CATEGORIES:
            raise SeedError(f"{where}: unknown category {raw.get('category')!r}")
        unit = raw.get("weight_unit")
        if unit is not None and unit not in WEIGHT_UNITS:
            raise SeedError(f"{where}: weight_unit must be one of {WEIGHT_UNITS} or null")
        if (raw.get("weight_value") is None) != (unit is None):
            raise SeedError(f"{where}: weight_value and weight_unit must both be set or both null")
        status = raw.get("status")
        if status not in (None, "tbd"):
            raise SeedError(f"{where}: status may only be 'tbd' (or omitted), got {status!r}")

        if uses_relative:
            offset = raw.get("due_in_days")
            due = today + timedelta(days=offset) if offset is not None else None
        else:
            due = raw.get("due_date")
            if due is not None and not isinstance(due, date):
                raise SeedError(f"{where}: due_date must be YYYY-MM-DD, got {due!r}")

        assignments.append(
            Assignment(
                id=aid,
                course_id=raw["course_id"],
                title=raw["title"],
                category=raw["category"],
                due_date=due,
                due_time=_parse_time(raw.get("due_time"), where),
                weight_value=raw.get("weight_value"),
                weight_unit=unit,
                is_team=bool(raw.get("is_team", False)),
                date_tbd=status == "tbd" or due is None,
                notes=(raw.get("notes") or "").strip() or None,
            )
        )
    return assignments


def load_seed(session: Session, seed_dir: Path, today: date | None = None) -> str:
    """Replace all rows with the contents of the seed files. Returns the kind loaded.

    User state (completion and estimate overrides) is carried over by
    assignment id, so re-seeding after editing the YAML — e.g. when a
    professor finally publishes a TBD date — doesn't lose your checkmarks.
    """
    today = today or date.today()
    files = find_seed_files(seed_dir)
    rules = _parse_rules(_read_yaml(files.rules))
    courses = _parse_courses(_read_yaml(files.courses))
    assignments = _parse_assignments(
        _read_yaml(files.assignments), {c.id for c in courses}, today
    )

    completed = {
        a.id: a.completed_at
        for a in session.exec(select(Assignment).where(Assignment.completed_at.is_not(None)))
    }
    overrides = {
        e.assignment_id: e.override_hours
        for e in session.exec(select(TimeEstimate).where(TimeEstimate.override_hours.is_not(None)))
    }
    for a in assignments:
        a.completed_at = completed.get(a.id)

    for model in (TimeEstimate, Assignment, Course, EstimateRule):
        for row in session.exec(select(model)).all():
            session.delete(row)
    session.flush()

    session.add_all(EstimateRule(category=k, default_hours=v) for k, v in rules.items())
    session.add_all(courses)
    session.flush()
    session.add_all(assignments)
    session.flush()
    session.add_all(
        TimeEstimate(
            assignment_id=a.id,
            category_default_hours=rules[a.category],
            override_hours=overrides.get(a.id),
        )
        for a in assignments
    )
    session.commit()
    return files.kind


def is_seeded(session: Session) -> bool:
    return session.exec(select(Course).limit(1)).first() is not None
