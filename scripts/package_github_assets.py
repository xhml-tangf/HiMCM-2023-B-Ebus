"""Build the large, reproducible data bundle for a GitHub Release."""
from __future__ import annotations

import argparse
import hashlib
import json
import tarfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NAME = "himcm-complete-data-2026-10-25.tar.gz"
SOURCE_DIRS = (Path("materials"), Path("data"), Path("results"))


def included(path: Path) -> bool:
    return not any(part in {"__pycache__", ".pytest_cache"} for part in path.parts)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=ROOT / "tmp/github_assets")
    parser.add_argument("--name", default=DEFAULT_NAME)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    archive = args.output_dir / args.name
    started = time.time()
    count = total = 0
    with tarfile.open(archive, "w:gz", compresslevel=6) as bundle:
        for base in SOURCE_DIRS:
            root = ROOT / base
            if not root.is_dir():
                continue
            for path in sorted(root.rglob("*")):
                if not path.is_file() or not included(path):
                    continue
                bundle.add(path, arcname=path.relative_to(ROOT).as_posix(), recursive=False)
                count += 1
                total += path.stat().st_size
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    record = {
        "archive": archive.name,
        "status": "local; upload to GitHub Release",
        "bytes": archive.stat().st_size,
        "uncompressed_bytes": total,
        "files": count,
        "sha256": digest,
        "contents": [p.as_posix() for p in SOURCE_DIRS],
        "elapsed_seconds": round(time.time() - started, 1),
    }
    out = ROOT / "release/github_assets.json"
    out.write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(json.dumps({**record, "path": str(archive)}, indent=2))


if __name__ == "__main__":
    main()
