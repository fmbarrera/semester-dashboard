from datetime import UTC, datetime, timedelta

import pytest
import yaml
from sqlmodel import Session, SQLModel, select

from dashboard.models import Assignment, TimeEstimate
from dashboard.seed import SeedError, find_seed_files, load_seed

from .conftest import TODAY


@pytest.fixture
def session(engine):
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def edit_yaml(path, fn):
    data = yaml.safe_load(path.read_text())
    fn(data)
    path.write_text(yaml.safe_dump(data))


def test_falls_back_to_sample_files(seed_dir):
    assert find_seed_files(seed_dir).kind == "sample"


def test_prefers_local_pair(seed_dir):
    (seed_dir / "courses.local.yaml").write_text("courses: []")
    (seed_dir / "assignments.local.yaml").write_text("assignments: []")
    assert find_seed_files(seed_dir).kind == "local"


def test_half_a_local_pair_is_an_error(seed_dir):
    (seed_dir / "courses.local.yaml").write_text("courses: []")
    with pytest.raises(SeedError, match="pair"):
        find_seed_files(seed_dir)


def test_relative_dates_resolve_against_today(session, seed_dir):
    load_seed(session, seed_dir, TODAY)
    quiz = session.get(Assignment, "bus101-quiz1")  # due_in_days: -3
    assert quiz.due_date == TODAY - timedelta(days=3)


def test_null_date_is_tbd(session, seed_dir):
    load_seed(session, seed_dir, TODAY)
    final = session.get(Assignment, "eco250-final-exam")
    assert final.due_date is None and final.date_tbd


def test_every_assignment_gets_a_default_estimate(session, seed_dir):
    load_seed(session, seed_dir, TODAY)
    n_assignments = len(session.exec(select(Assignment)).all())
    estimates = session.exec(select(TimeEstimate)).all()
    assert len(estimates) == n_assignments
    exam = session.get(TimeEstimate, "bus101-midterm")
    assert exam.category_default_hours == 4.0


def test_reseed_preserves_completion_and_overrides(session, seed_dir):
    load_seed(session, seed_dir, TODAY)
    a = session.get(Assignment, "bus101-case1")
    a.completed_at = datetime(2026, 10, 1, tzinfo=UTC)
    session.get(TimeEstimate, "bus101-midterm").override_hours = 9.0
    session.commit()

    load_seed(session, seed_dir, TODAY)
    assert session.get(Assignment, "bus101-case1").completed_at is not None
    assert session.get(TimeEstimate, "bus101-midterm").override_hours == 9.0
    assert session.get(Assignment, "bus101-quiz1").completed_at is None


@pytest.mark.parametrize(
    "mutate,message",
    [
        (lambda d: d["assignments"][0].update(course_id="nope"), "unknown course_id"),
        (lambda d: d["assignments"][0].update(category="essay"), "unknown category"),
        (lambda d: d["assignments"][1].update(id=d["assignments"][0]["id"]), "duplicate id"),
        (lambda d: d["assignments"][0].update(due_time="9am"), "HH:MM"),
        (lambda d: d["assignments"][0].update(weight_unit=None), "both be set"),
        (lambda d: d["assignments"][0].update(due_date="2026-10-01"), "mixes"),
        (lambda d: d["assignments"][0].update(status="done"), "status"),
    ],
)
def test_invalid_assignment_data_is_rejected(session, seed_dir, mutate, message):
    edit_yaml(seed_dir / "assignments.sample.yaml", mutate)
    with pytest.raises(SeedError, match=message):
        load_seed(session, seed_dir, TODAY)


def test_failed_seed_leaves_existing_data_intact(session, seed_dir):
    load_seed(session, seed_dir, TODAY)
    edit_yaml(
        seed_dir / "assignments.sample.yaml",
        lambda d: d["assignments"][0].update(category="essay"),
    )
    with pytest.raises(SeedError):
        load_seed(session, seed_dir, TODAY)
    assert session.get(Assignment, "bus101-quiz1") is not None


def test_missing_estimate_rule_is_rejected(session, seed_dir):
    edit_yaml(seed_dir / "estimate_rules.yaml", lambda d: d["categories"].pop("quiz"))
    with pytest.raises(SeedError, match="quiz"):
        load_seed(session, seed_dir, TODAY)
