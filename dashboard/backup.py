"""Timestamped backups of the database and the gitignored real seed data.

Neither data/dashboard.db nor seed/*.local.yaml is in git, so without a
backup they exist only on this machine. Point config.local.yaml's
`backup_dir` at a synced folder (iCloud, Dropbox, ...) to keep copies there.
"""

import hashlib
import shutil
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path

SUBFOLDER = "Semester Dashboard Backups"
KEEP = 30


def _fingerprint(files: list[Path]) -> str:
    h = hashlib.sha256()
    for f in files:
        h.update(f.name.encode())
        h.update(f.read_bytes())
    return h.hexdigest()


def backup(
    db_path: Path,
    seed_dir: Path,
    backup_dir: Path,
    keep: int = KEEP,
    now: datetime | None = None,
) -> Path | None:
    """Write a snapshot folder and return it, or None if nothing changed.

    Uses SQLite's online backup API rather than a file copy, so the
    snapshot is consistent even if the server is mid-write.
    """
    if not db_path.exists():
        return None
    if not backup_dir.is_dir():
        raise FileNotFoundError(f"Backup folder not found: {backup_dir}")

    root = backup_dir / SUBFOLDER
    root.mkdir(exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        staged = Path(tmp)
        src = sqlite3.connect(db_path)
        dst = sqlite3.connect(staged / db_path.name)
        try:
            src.backup(dst)
        finally:
            src.close()
            dst.close()
        for yaml_file in sorted(seed_dir.glob("*.local.yaml")):
            shutil.copy2(yaml_file, staged / yaml_file.name)

        files = sorted(staged.iterdir())
        digest = _fingerprint(files)
        previous = _snapshots(root)
        if previous and (previous[-1] / "SHA256").read_text().strip() == digest:
            return None

        now = now or datetime.now()
        dest = root / now.strftime("%Y-%m-%d_%H%M%S")
        dest.mkdir()
        for f in files:
            shutil.copy2(f, dest / f.name)
        (dest / "SHA256").write_text(digest + "\n")

    for old in _snapshots(root)[:-keep]:
        shutil.rmtree(old)
    return dest


def _snapshots(root: Path) -> list[Path]:
    """Complete snapshot folders, oldest first (names sort chronologically)."""
    return sorted(p for p in root.iterdir() if p.is_dir() and (p / "SHA256").exists())
