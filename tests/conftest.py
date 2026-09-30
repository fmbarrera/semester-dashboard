import shutil
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import create_engine

from dashboard.api import create_app

REPO_SEED = Path(__file__).parent.parent / "seed"
TODAY = date(2026, 10, 1)


@pytest.fixture
def seed_dir(tmp_path):
    """Sample seed files only — never the gitignored *.local.yaml real data."""
    for name in ("courses.sample.yaml", "assignments.sample.yaml", "estimate_rules.yaml"):
        shutil.copy(REPO_SEED / name, tmp_path / name)
    return tmp_path


@pytest.fixture
def engine():
    return create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )


@pytest.fixture
def client(engine, seed_dir):
    app = create_app(engine, seed_dir, today=lambda: TODAY)
    with TestClient(app) as c:
        yield c
