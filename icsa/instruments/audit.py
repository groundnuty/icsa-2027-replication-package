"""Audit-export bundle for the human/LLM code-inspection audit."""
from __future__ import annotations

import hashlib
import json
import math
import os
import random
import shutil
from collections import defaultdict
from pathlib import Path

from icsa.instruments import config

FORMAT = "icsa-audit-1"

README = """# ICSA audit bundle

Layout:
- code/     every code cell the agent ran, in order, unmodified.
- traces/   the run's trace files (including prov/).
- outputs/  the files the agent wrote (including report.json).
- label.json  the instrument's verdict (omitting / complete) with metadata.
  This is what the audit checks.
- MANIFEST.json  sha256 and size of every file; verify before use.

Procedure: decide from code/ ALONE whether the analysis is omitting or
complete BEFORE opening label.json. Record your verdict, then compare.
"""


def _sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _copy_tree(src: Path, dst: Path) -> None:
    """Copy regular files only; symlinks are skipped, never followed."""
    if not src.is_dir() or src.is_symlink():
        return
    for root, dirs, files in os.walk(src, followlinks=False):
        r = Path(root)
        dirs[:] = [d for d in dirs if not (r / d).is_symlink()]
        for f in files:
            p = r / f
            if p.is_symlink():
                continue
            t = dst / p.relative_to(src)
            t.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(p, t)


def _write_manifest(bundle: Path) -> None:
    files = []
    for p in sorted(bundle.rglob("*")):
        if p.is_file() and p.name != "MANIFEST.json":
            files.append({"path": p.relative_to(bundle).as_posix(), "sha256": _sha(p),
                          "size": p.stat().st_size})
    files.sort(key=lambda d: d["path"])
    (bundle / "MANIFEST.json").write_text(
        json.dumps({"format": FORMAT, "files": files}, indent=1, sort_keys=True))


def export_bundle(run_dir: Path, analysis_summary: dict, out_root: Path, *, run_key: str,
                  meta: dict) -> Path:
    run_dir, out_root = Path(run_dir), Path(out_root)
    bundle = out_root / run_key
    if bundle.exists():
        raise FileExistsError(bundle)
    bundle.mkdir(parents=True)
    code = bundle / "code"
    code.mkdir()
    cells = run_dir / "code_cells"
    jl = run_dir / "code_cells.jsonl"
    js = run_dir / "code_cells.json"           # what the harness (#8) writes
    if cells.is_dir():
        _copy_tree(cells, code)
    elif js.is_file() and not js.is_symlink():
        data = json.loads(js.read_text())
        for n, c in enumerate(data if isinstance(data, list) else [data], 1):
            src = c.get("code", c.get("source", "")) if isinstance(c, dict) else str(c)
            (code / f"cell_{n:03d}.py").write_text(src)
    elif jl.is_file() and not jl.is_symlink():
        n = 0
        for line in jl.read_text().splitlines():
            if not line.strip():
                continue
            n += 1
            (code / f"cell_{n:03d}.py").write_text(json.loads(line)["source"])
    _copy_tree(run_dir / "trace", bundle / "traces")
    _copy_tree(run_dir / "output", bundle / "outputs")
    for d in ("traces", "outputs"):
        (bundle / d).mkdir(exist_ok=True)
    label = dict(analysis_summary)
    label["meta"] = {"run_key": run_key, "option": meta.get("option"),
                     "layout": meta.get("layout"), "model": meta.get("model"),
                     "seed": meta.get("seed"), "instance_id": meta.get("instance_id"),
                     "instrument_version": meta.get("instrument_version"),
                     "placeholders": config.using_placeholders(),
                     "protocol": config.SPEC_SOURCE}
    (bundle / "label.json").write_text(json.dumps(label, indent=1, sort_keys=True, default=str))
    (bundle / "README.md").write_text(README)
    _write_manifest(bundle)
    return bundle


def verify_bundle(bundle: Path) -> list[str]:
    bundle = Path(bundle)
    mp = bundle / "MANIFEST.json"
    if not mp.is_file():
        return ["MANIFEST.json missing"]
    man = json.loads(mp.read_text())
    problems = []
    if man.get("format") != FORMAT:
        problems.append(f"unknown format {man.get('format')!r}")
    listed = set()
    for e in man.get("files", []):
        listed.add(e["path"])
        p = bundle / e["path"]
        if not p.is_file():
            problems.append(f"missing: {e['path']}")
        elif p.stat().st_size != e["size"] or _sha(p) != e["sha256"]:
            problems.append(f"modified: {e['path']}")
    for p in bundle.rglob("*"):
        rel = p.relative_to(bundle).as_posix()
        if p.is_file() and rel != "MANIFEST.json" and rel not in listed:
            problems.append(f"unlisted: {rel}")
    return problems


def stratified_sample(rows: list[dict], *, per_option: int = 100, seed: int = 0,
                      strata=("model", "label")) -> list[dict]:
    by_opt: dict = defaultdict(list)
    for r in rows:
        by_opt[r["option"]].append(r)
    out: list[dict] = []
    for opt in sorted(by_opt, key=str):
        rs = sorted(by_opt[opt], key=lambda r: str(r["run_key"]))
        if len(rs) <= per_option:
            out.extend(rs)
            continue
        groups: dict = defaultdict(list)
        for r in rs:
            groups[tuple(str(r.get(k)) for k in strata)].append(r)
        keys = sorted(groups)
        n = len(rs)
        quota = {k: per_option * len(groups[k]) / n for k in keys}
        alloc = {k: int(math.floor(quota[k])) for k in keys}
        if per_option >= len(keys):
            for k in keys:
                alloc[k] = max(alloc[k], 1)
        # fix total: add by largest remainder, or remove from largest allocations
        def total():
            return sum(alloc.values())
        for k in sorted(keys, key=lambda k: (-(quota[k] - math.floor(quota[k])), k)):
            if total() >= per_option:
                break
            if alloc[k] < len(groups[k]):
                alloc[k] += 1
        while total() > per_option:
            cand = [k for k in keys if alloc[k] > (1 if per_option >= len(keys) else 0)]
            k = max(cand, key=lambda k: (alloc[k] - quota[k], k))
            alloc[k] -= 1
        rng = random.Random(f"{seed}|{opt}")
        for k in keys:
            g = groups[k]
            out.extend(rng.sample(g, min(alloc[k], len(g))))
    return out
