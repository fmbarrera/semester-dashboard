"""Run the dashboard: `python app.py` (add --reseed after editing seed/*.yaml).

By default it listens on this machine only (127.0.0.1), so it's safe on
public wifi: the app has no login, and anyone who can reach it can read and
change your data. Add --lan on a trusted network (e.g. home wifi) to open
it from your phone at the address it prints.

If config.local.yaml sets `backup_dir`, the database and real seed files
are backed up there on startup and again on shutdown (see
config.example.yaml).
"""

import argparse
import os
import socket
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


LOCAL_ONLY = "127.0.0.1"
ALL_INTERFACES = "0.0.0.0"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    where = parser.add_mutually_exclusive_group()
    where.add_argument(
        "--lan",
        action="store_true",
        help="Also accept connections from other devices on this network, "
        "e.g. your phone. Only use on a network you trust.",
    )
    where.add_argument(
        "--host",
        help=f"Advanced: exact address to listen on (default {LOCAL_ONLY}).",
    )
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--reseed",
        action="store_true",
        help="Reload seed/*.yaml into the database, keeping completion "
        "state and estimate overrides for assignments that still exist.",
    )
    args = parser.parse_args(argv)
    if args.host is None:
        args.host = ALL_INTERFACES if args.lan else LOCAL_ONLY
    return args


def lan_ip() -> str | None:
    """This machine's address on the local network (no packets are sent)."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("10.255.255.255", 1))
            return s.getsockname()[0]
        except OSError:
            return None


def announce(args: argparse.Namespace) -> None:
    if args.host == LOCAL_ONLY:
        print(f"Dashboard: http://localhost:{args.port}  (this computer only)")
        return
    ip = lan_ip()
    print(f"Dashboard: http://localhost:{args.port}")
    if ip:
        print(f"From your phone (same wifi): http://{ip}:{args.port}")
    print(
        "WARNING: other devices on this network can open the dashboard, and it has\n"
        "no login. Only use --lan on a network you trust, like home wifi."
    )


def main() -> None:
    args = parse_args()
    config = load_config()

    run_backup(config)  # before --reseed, so there's always a pre-reseed copy
    if args.reseed:
        SQLModel.metadata.create_all(engine)
        with Session(engine) as session:
            kind = load_seed(session, SEED_DIR)
        print(f"Reseeded from {kind} seed files.")

    announce(args)
    try:
        uvicorn.run(app, host=args.host, port=args.port)
    finally:
        run_backup(config)  # capture this session's changes on Ctrl+C


if __name__ == "__main__":
    main()
