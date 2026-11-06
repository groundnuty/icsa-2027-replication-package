"""Verify (default) or write checksums.sha256: the sha256 of every file of this package except checksums.sha256 itself.

    python3 reproduce/checksums.py            # verify; the last line reads `verify: all N files match checksums.sha256`
    python3 reproduce/checksums.py --write    # rewrite checksums.sha256 from the files on disk

Standard library only. Files under .git/, build/ (where the checks write) and .venv/ are not listed.
"""
from __future__ import annotations

import hashlib
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SUMS = ROOT / "checksums.sha256"
SKIP_DIRS = {".git", ".draft", "build", "__pycache__", ".venv"}


def files() -> list[str]:
    out = []
    for p in ROOT.rglob("*"):
        rel = p.relative_to(ROOT)
        if p.is_file() and not set(rel.parts) & SKIP_DIRS and rel.as_posix() != "checksums.sha256":
            out.append(rel.as_posix())
    return sorted(out)


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main(argv: list[str]) -> int:
    if argv[1:] == ["--write"]:
        SUMS.write_text("".join(f"{sha256(ROOT / f)}  {f}\n" for f in files()), encoding="utf-8")
        print(f"wrote checksums.sha256: {len(files())} files")
        return 0
    if argv[1:]:
        print(__doc__)
        return 2
    want = {}
    for line in SUMS.read_text(encoding="utf-8").splitlines():
        digest, _, name = line.partition("  ")
        want[name] = digest
    have = set(files())
    bad = [f"missing: {n}" for n in sorted(set(want) - have)]
    bad += [f"not listed: {n}" for n in sorted(have - set(want))]
    bad += [f"differs: {n}" for n in sorted(set(want) & have) if sha256(ROOT / n) != want[n]]
    for line in bad:
        print(line)
    if bad:
        print(f"verify: FAILED, {len(bad)} of {len(want)} entries")
        return 1
    print(f"verify: all {len(want)} files match checksums.sha256")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
