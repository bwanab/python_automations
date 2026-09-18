#!/usr/bin/env python3
"""
Fix DigiKam's AlbumRoots identifier after a macOS update changes the disk UUID.
"""

import re
import shutil
import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path

default_path = Path("~/Documents/base_images/digikam4.db").expanduser()


def is_digikam_running() -> bool:
    """Return True if a DigiKam process is currently running."""
    result = subprocess.run(
        ["pgrep", "-i", "-x", "digikam"], capture_output=True, text=True
    )
    return result.returncode == 0


def get_disk_uuid(mount_point: str = "/") -> str:
    """Get the UUID of the disk at the given mount point using diskutil."""
    result = subprocess.run(
        ["diskutil", "info", mount_point], capture_output=True, text=True, check=True
    )
    for line in result.stdout.splitlines():
        if "Volume UUID" in line:
            uuid = line.split(":", 1)[1].strip()
            return uuid
    raise RuntimeError(f"Could not find Volume UUID for mount point: {mount_point}")


def get_current_identifier(db_path: Path) -> str:
    """Read the current identifier from AlbumRoots."""
    with sqlite3.connect(db_path) as conn:
        total = conn.execute("SELECT COUNT(*) FROM AlbumRoots").fetchone()[0]
        row = conn.execute("SELECT identifier FROM AlbumRoots WHERE id = 1").fetchone()
    if not row:
        raise RuntimeError("No row with id=1 found in AlbumRoots")
    if total > 1:
        print(
            f"  WARNING: AlbumRoots has {total} rows; only id=1 will be updated. "
            f"Other roots (e.g. external drives) will not be touched."
        )
    return row[0]


def extract_uuid_from_identifier(identifier: str) -> str | None:
    """Pull the UUID out of a 'volumeid:?uuid=XXXX' string."""
    match = re.search(r"[?&]uuid=([A-F0-9-]+)", identifier, re.IGNORECASE)
    return match.group(1) if match else None


def update_identifier(
    db_path: Path, current_identifier: str, new_uuid: str, dry_run: bool = False
) -> None:
    """Update AlbumRoots.identifier with the new UUID, preserving other params."""
    new_identifier, count = re.subn(
        r"([?&]uuid=)[A-F0-9-]+",
        rf"\g<1>{new_uuid}",
        current_identifier,
        flags=re.IGNORECASE,
    )
    if count != 1:
        raise RuntimeError(
            f"Expected exactly one 'uuid=' parameter to replace in identifier, "
            f"found {count}: {current_identifier!r}"
        )

    if dry_run:
        print(f"  [dry-run] Would set identifier → {new_identifier}")
        return

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE AlbumRoots SET identifier = ? WHERE id = 1", (new_identifier,)
        )
        conn.commit()
    print(f"  Updated identifier → {new_identifier}")


def backup_db(db_path: Path) -> Path:
    """Copy the database to a timestamped backup file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db_path.with_suffix(f".{timestamp}.bak")
    shutil.copy2(db_path, backup_path)
    print(f"  Backup written to: {backup_path}")
    return backup_path


def fix_digikam_uuid(
    db_path: Path | str = default_path,
    mount_point: str = "/",
    dry_run: bool = False,
) -> None:
    db_path = Path(db_path).expanduser()

    if is_digikam_running():
        raise SystemExit(
            "Error: DigiKam is currently running. Quit DigiKam and re-run this script."
        )

    if not db_path.exists():
        raise FileNotFoundError(f"DigiKam database not found: {db_path}")

    print(f"DigiKam DB : {db_path}")

    current_identifier = get_current_identifier(db_path)
    print(f"  Current identifier: {current_identifier}")
    db_uuid = extract_uuid_from_identifier(current_identifier)
    disk_uuid = get_disk_uuid(mount_point)

    print(f"DB uuid    : {db_uuid}")
    print(f"Disk uuid  : {disk_uuid}")

    if db_uuid and db_uuid.upper() == disk_uuid.upper():
        print("✓ UUIDs already match — nothing to do.")
        return

    print("✗ UUID mismatch — fixing...")
    if not dry_run:
        backup_db(db_path)
    update_identifier(db_path, current_identifier, disk_uuid, dry_run=dry_run)
    print("Done.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Sync DigiKam's AlbumRoots UUID with the current macOS disk UUID"
    )
    parser.add_argument(
        "--db",
        default=default_path,
        help=f"Path to digikam4.db (default: {default_path})",
    )
    parser.add_argument(
        "--mount",
        default="/",
        help="Mount point of the volume (default: /)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without modifying anything",
    )
    args = parser.parse_args()

    fix_digikam_uuid(db_path=args.db, mount_point=args.mount, dry_run=args.dry_run)
