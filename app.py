"""Run the dashboard: `python app.py` (add --reseed after editing seed/*.yaml).

Binds to 0.0.0.0 so it's reachable from a phone on the same wifi at
http://<mac-lan-ip>:8000.
"""

import argparse
import os
from pathlib import Path

import uvicorn
from sqlmodel import Session, SQLModel, create_engine

from dashboard.api import create_app
from dashboard.seed import load_seed

ROOT = Path(__file__).parent
DB_PATH = Path(os.environ.get("DASHBOARD_DB", ROOT / "data" / "dashboard.db"))
SEED_DIR = Path(os.environ.get("DASHBOARD_SEED_DIR", ROOT / "seed"))

DB_PATH.parent.mkdir(parents=True, exist_ok=True)
engine = create_engine(f"sqlite:///{DB_PATH}")
app = create_app(engine, SEED_DIR)


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

    if args.reseed:
        SQLModel.metadata.create_all(engine)
        with Session(engine) as session:
            kind = load_seed(session, SEED_DIR)
        print(f"Reseeded from {kind} seed files.")

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
