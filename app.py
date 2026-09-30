"""Run the dashboard: `python app.py` (add --reseed after editing seed/*.yaml).

Binds to 0.0.0.0 so it's reachable from a phone on the same wifi at
http://<mac-lan-ip>:8000.

If config.local.yaml sets `backup_dir`, the database and real seed files
are backed up there on startup and again on shutdown (see
config.example.yaml).
"""

import argparse
import os
from pathlib import Path

import uvicorn
import yaml
from sqlmodel import Session, SQLModel, create_engine

from dashboard.api import create_app
from dashboard.backup import backup
from dashboard.seed import load_seed

ROOT = Path(__file__).parent
DB_PATH = Path(os.environ.get("DASHBOARD_DB", ROOT / "data" / "dashboard.db"))
SEED_DIR = Path(os.environ.get("DASHBOARD_SEED_DIR", ROOT / "seed"))
CONFIG_PATH = ROOT / "config.local.yaml"

DB_PATH.parent.mkdir(parents=True, exist_ok=True)
engine = create_engine(f"sqlite:///{DB_PATH}")
app = create_app(engine, SEED_DIR)


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    with CONFIG_PATH.open() as f:
        return yaml.safe_load(f) or {}


def run_backup(config: dict) -> None:
    """Back up if configured. Never stops the app from starting."""
    backup_dir = config.get("backup_dir")
    if not backup_dir:
        return
    try:
        dest = backup(DB_PATH, SEED_DIR, Path(backup_dir).expanduser())
    except Exception as exc:  # noqa: BLE001 — a failed backup must not block the app
        print(f"WARNING: backup failed: {exc}")
        return
    print(f"Backed up to {dest}" if dest else "Backup skipped: nothing changed since the last one.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--reseed",
        action="store_true",
        help="Reload seed/*.yaml into the database, keeping completion "
        "state and estimate overrides for assignments that still exist.",
    )
    args = parser.parse_args()
    config = load_config()

    run_backup(config)  # before --reseed, so there's always a pre-reseed copy
    if args.reseed:
        SQLModel.metadata.create_all(engine)
        with Session(engine) as session:
            kind = load_seed(session, SEED_DIR)
        print(f"Reseeded from {kind} seed files.")

    try:
        uvicorn.run(app, host=args.host, port=args.port)
    finally:
        run_backup(config)  # capture this session's changes on Ctrl+C


if __name__ == "__main__":
    main()
