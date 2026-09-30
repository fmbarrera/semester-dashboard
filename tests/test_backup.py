import sqlite3
from datetime import datetime, timedelta

import pytest

from dashboard.backup import SUBFOLDER, backup

T0 = datetime(2026, 9, 30, 12, 0, 0)


@pytest.fixture
def paths(tmp_path):
    db = tmp_path / "data" / "dashboard.db"
    db.parent.mkdir()
    with sqlite3.connect(db) as conn:
        conn.execute("create table t (x)")
        conn.execute("insert into t values (1)")
    conn.close()
    seed = tmp_path / "seed"
    seed.mkdir()
    (seed / "courses.local.yaml").write_text("courses: []")
    (seed / "courses.sample.yaml").write_text("not backed up")
    dest = tmp_path / "icloud"
    dest.mkdir()
    return db, seed, dest


def add_row(db):
    conn = sqlite3.connect(db)
    with conn:
        conn.execute("insert into t values (2)")
    conn.close()


def test_snapshot_contains_db_and_local_seed_files(paths):
    db, seed, dest = paths
    snap = backup(db, seed, dest, now=T0)
    assert snap == dest / SUBFOLDER / "2026-09-30_120000"
    assert sorted(p.name for p in snap.iterdir()) == [
        "SHA256",
        "courses.local.yaml",
        "dashboard.db",
    ]
    conn = sqlite3.connect(snap / "dashboard.db")
    assert conn.execute("select x from t").fetchall() == [(1,)]
    conn.close()


def test_unchanged_data_is_not_backed_up_twice(paths):
    db, seed, dest = paths
    assert backup(db, seed, dest, now=T0) is not None
    assert backup(db, seed, dest, now=T0 + timedelta(minutes=1)) is None

    add_row(db)
    assert backup(db, seed, dest, now=T0 + timedelta(minutes=2)) is not None


def test_seed_edit_alone_triggers_backup(paths):
    db, seed, dest = paths
    backup(db, seed, dest, now=T0)
    (seed / "courses.local.yaml").write_text("courses: [changed]")
    assert backup(db, seed, dest, now=T0 + timedelta(minutes=1)) is not None


def test_keeps_only_newest_snapshots(paths):
    db, seed, dest = paths
    for i in range(5):
        add_row(db)
        backup(db, seed, dest, keep=3, now=T0 + timedelta(minutes=i))
    kept = sorted(p.name for p in (dest / SUBFOLDER).iterdir())
    assert kept == ["2026-09-30_120200", "2026-09-30_120300", "2026-09-30_120400"]


def test_no_database_yet_is_a_no_op(paths):
    db, seed, dest = paths
    db.unlink()
    assert backup(db, seed, dest) is None
    assert not (dest / SUBFOLDER).exists()


def test_missing_backup_folder_raises(paths):
    db, seed, dest = paths
    with pytest.raises(FileNotFoundError):
        backup(db, seed, dest / "nope")
