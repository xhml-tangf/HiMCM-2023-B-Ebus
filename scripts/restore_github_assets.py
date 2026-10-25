"""Restore the large data bundle attached to the project's GitHub Release.

The archive contains top-level ``materials``, ``data`` and ``results``
directories. Extraction is restricted to the project's writable subtree.
"""
from __future__ import annotations

import argparse
import tarfile
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
ALLOWED = (Path("materials"), Path("data"), Path("results"))


def safe_member(name: str) -> bool:
    path = PurePosixPath(name)
    return bool(path.parts) and path.parts[0] in {p.as_posix() for p in ALLOWED} and ".." not in path.parts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True, type=Path)
    args = parser.parse_args()
    archive = args.archive.resolve()
    if not archive.is_file():
        raise SystemExit(f"Archive not found: {archive}")
    with tarfile.open(archive, "r:gz") as bundle:
        members = bundle.getmembers()
        unsafe = [m.name for m in members if not safe_member(m.name)]
        if unsafe:
            raise SystemExit(f"Refusing archive with paths outside project data folders: {unsafe[:3]}")
        bundle.extractall(ROOT, filter="data")
    print(f"Restored {len(members)} entries from {archive.name} into {ROOT}")


if __name__ == "__main__":
    main()
