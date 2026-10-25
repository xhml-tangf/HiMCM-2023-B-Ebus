"""Copy the current paper and standalone LaTeX archive to release/."""
from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper/claude_plan/latex"
RELEASE = ROOT / "release"


def main() -> None:
    RELEASE.mkdir(exist_ok=True)
    shutil.copy2(PAPER / "main.pdf", RELEASE / "charging_ahead_claude_plan.pdf")
    source_zip = RELEASE / "charging_ahead_latex_source.zip"
    with zipfile.ZipFile(source_zip, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(PAPER.rglob("*")):
            if path.is_file() and path.suffix in {".tex", ".png", ".md", ".json"}:
                archive.write(path, path.relative_to(PAPER).as_posix())
    manifest = {}
    for path in (RELEASE / "charging_ahead_claude_plan.pdf", source_zip):
        manifest[path.name] = {"bytes": path.stat().st_size,
                               "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    (RELEASE / "release_files.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
