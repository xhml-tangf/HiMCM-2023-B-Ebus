"""Prefetch official Tectonic resources for the existing 12-point manuscript.

This only populates a compiler cache; it does not compile or export a PDF.
Use --cache-dir with the directory actually used by the built-in editor.
The existing v33 index supplies byte ranges, avoiding a full TeXLive download.
"""

from __future__ import annotations

import argparse
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

URL = "https://relay.fullyjustified.net/default_bundle_v33.tar"
PACKAGES = {
    "size12.clo", "geometry.sty", "keyval.sty", "ifvtex.sty", "iftex.sty",
    "amsmath.sty", "amssymb.sty", "amsfonts.sty", "booktabs.sty", "longtable.sty",
    "array.sty", "enumitem.sty", "graphicx.sty", "graphics.sty", "trig.sty",
    "graphics.cfg", "xetex.def", "fancyhdr.sty", "lmodern.sty", "fontenc.sty",
    "placeins.sty",
    "t1enc.def", "t1lmr.fd", "t1lmtt.fd", "t1lmss.fd", "omllmm.fd",
    "omslmsy.fd", "omxlmex.fd", "ot1lmr.fd", "ts1lmr.fd", "ts1lmtt.fd",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--tectonic", type=Path,
                        help="Use the compiler's own bundle downloader when available")
    args = parser.parse_args()
    data_root = args.cache_dir / "bundles/data"
    index = next(data_root.glob("*.index"))
    destination = data_root / index.stem
    entries = []
    for line in index.read_text(encoding="utf-8").splitlines():
        name, offset, length = line.split()
        font = ((name.startswith("lm") and name.endswith((".otf", ".pfb")))
                or (name.startswith(("ec-lm", "cm")) and name.endswith(".tfm")))
        if (font or name in PACKAGES) and not (destination / name).is_file():
            entries.append((int(offset), int(length), name))
    entries.sort()
    if args.tectonic:
        environment = dict(os.environ, TECTONIC_CACHE_DIR=str(args.cache_dir))

        def fetch_with_compiler(entry: tuple[int, int, str]) -> int:
            result = subprocess.run([str(args.tectonic), "-X", "bundle", "cat", entry[2]],
                                    env=environment, stdout=subprocess.DEVNULL,
                                    stderr=subprocess.PIPE, timeout=120)
            if result.returncode:
                raise RuntimeError(f"Could not fetch {entry[2]}: "
                                   + result.stderr.decode("utf-8", "replace")[-300:])
            return 1

        print(f"Prefetching {len(entries)} resources using the compiler downloader", flush=True)
        with ThreadPoolExecutor(max_workers=4) as executor:
            total = sum(executor.map(fetch_with_compiler, entries))
        print(f"Cached {total} resources; no PDF was generated")
        return
    groups: list[list[tuple[int, int, str]]] = []
    for entry in entries:
        if (not groups or entry[0] - (groups[-1][-1][0] + groups[-1][-1][1]) > 512_000
                or entry[0] + entry[1] - groups[-1][0][0] > 8_000_000):
            groups.append([])
        groups[-1].append(entry)

    def fetch(group: list[tuple[int, int, str]]) -> int:
        start = group[0][0]
        end = group[-1][0] + group[-1][1] - 1
        response = requests.get(URL, headers={"Range": f"bytes={start}-{end}",
                                              "Accept-Encoding": "identity"},
                                timeout=90, stream=True)
        response.raise_for_status()
        if response.status_code != 206:
            response.close()
            raise RuntimeError("Bundle server did not honor byte range")
        content = response.content
        if len(content) != end - start + 1:
            raise RuntimeError("Truncated bundle range")
        for offset, length, name in group:
            (destination / name).write_bytes(content[offset-start:offset-start+length])
        return len(group)

    print(f"Prefetching {len(entries)} missing resources in {len(groups)} ranges", flush=True)
    with ThreadPoolExecutor(max_workers=4) as executor:
        total = sum(executor.map(fetch, groups))
    print(f"Cached {total} resources; no PDF was generated")


if __name__ == "__main__":
    main()
