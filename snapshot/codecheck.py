"""The code a snapshot ran against the code the campaign ran: refuse a snapshot whose pipeline or analysis is not the campaign's, byte for byte.

A snapshot reads the campaign's run directories with the pipeline and the analysis of the tree it runs from. The runs themselves were made by the
campaign's tree (the code that was frozen at the cut). `--campaign-tree PATH` names that tree on this host, and this module compares:

  static    every icsa file the pipeline and the analysis can import, by the frozen transitive import walk of `icsa.instruments.validate.code_files`
            (in-function imports included; it adds instruments/sim/*.py, a harmless superset), starting from ENTRIES, and every file under data/
            (the manifests, masks and indexes the pipeline reads), each by bytes against the same path in the campaign's tree. A file that differs, or
            is missing on either side, refuses the snapshot before anything is made.
  runtime   after the analysis ran, every icsa module that is actually loaded (`sys.modules`) must be in the static list and byte-equal to the
            campaign's file. A module outside the list means the walk missed an import: the run fails.
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import hashlib             # noqa: E402
from pathlib import Path    # noqa: E402

ENTRIES = (          # the files the snapshot's pipeline and analysis start from; the walk follows their imports
    "icsa/pipeline/postrun.py", "icsa/pipeline/resources.py", "icsa/pipeline/loadrec.py",
    "icsa/analysis/run.py", "icsa/analysis/adapter.py", "icsa/analysis/config.py", "icsa/analysis/inspection.py", "icsa/analysis/overhead.py",
    "icsa/campaign/export.py", "icsa/campaign/store.py",
    "icsa/instruments/validate.py",      # this module's own walk (`code_files`) is loaded from it, so it is code that ran; its imports come with it
)


class CodeCheckError(RuntimeError):
    pass


def tree_data_hash(repo_root) -> str:
    """sha256 over (relative path, sha256 of content) of every file under the tree's `data/`, in path order. The pipeline reads it (the instance
    manifest, the sea masks, the data manifests the full index's digest is checked against), and `codestamp.ROOTS` does not cover it."""
    root = Path(repo_root) / "data"
    files = sorted((f for f in root.rglob("*") if f.is_file()), key=lambda f: f.relative_to(root).as_posix()) if root.is_dir() else []
    h = hashlib.sha256()
    for f in files:
        h.update(f.relative_to(root).as_posix().encode() + b"\0" + hashlib.sha256(f.read_bytes()).digest())
    return h.hexdigest()


def static_files(root) -> list[str]:
    """Relative paths of every icsa file the snapshot's pipeline and analysis can import, from ENTRIES."""
    from icsa.instruments.validate import code_files
    return code_files(Path(root), entries=ENTRIES)


def data_files(*roots) -> list[str]:
    """Relative paths of every file under data/ in any of the trees."""
    out: set[str] = set()
    for r in roots:
        d = Path(r) / "data"
        if d.is_dir():
            out.update(p.relative_to(r).as_posix() for p in d.rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc")
    return sorted(out)


def _same(a: Path, b: Path) -> bool:
    if a.stat().st_size != b.stat().st_size:
        return False
    with open(a, "rb") as fa, open(b, "rb") as fb:
        while True:
            x, y = fa.read(1 << 20), fb.read(1 << 20)
            if x != y:
                return False
            if not x:
                return True


def compare(running_root, campaign_tree, files) -> dict:
    """{"files": n, "differ": [...], "missing": [...]}: each of `files` (relative paths) by bytes in the two trees; missing on either side is `missing`."""
    running_root, campaign_tree = Path(running_root), Path(campaign_tree)
    differ, missing = [], []
    for rel in files:
        a, b = running_root / rel, campaign_tree / rel
        if not a.is_file() or not b.is_file():
            missing.append(rel)
        elif not _same(a, b):
            differ.append(rel)
    return {"files": len(files), "differ": differ, "missing": missing}


def static_check(running_root, campaign_tree) -> dict:
    """The static comparison: the import walk's files, and every file under data/. `static` is the walk's list (kept for the runtime check)."""
    static = static_files(running_root)
    code = compare(running_root, campaign_tree, static)
    data = compare(running_root, campaign_tree, data_files(running_root, campaign_tree))
    return {**code, "data_files": data["files"], "data_differ": data["differ"], "data_missing": data["missing"], "static": static}


def refusal(check: dict) -> str | None:
    """The reason to refuse before anything is made, or None. Names are code paths, not results."""
    bad = [("files differ from the campaign tree", check["differ"]), ("files are missing from one of the trees", check["missing"]),
           ("data files differ from the campaign tree", check["data_differ"]), ("data files are missing from one of the trees", check["data_missing"])]
    parts = [f"{len(v)} {what}: {', '.join(v[:5])}{', ...' if len(v) > 5 else ''}" for what, v in bad if v]
    return "code check: " + "; ".join(parts) if parts else None


def runtime_files(running_root) -> list[str]:
    """Relative paths of every module in `sys.modules` whose file is under the running tree's icsa/."""
    root = Path(running_root).resolve() / "icsa"
    out: set[str] = set()
    for m in list(sys.modules.values()):
        f = getattr(m, "__file__", None)
        if not f:
            continue
        try:
            out.add("icsa/" + Path(f).resolve().relative_to(root).as_posix())
        except (ValueError, OSError):
            continue
    return sorted(out)


def runtime_check(running_root, campaign_tree, static: list[str]) -> dict:
    """What was loaded against the walk and the campaign's files. `runtime_not_in_static` and `runtime_differ` must be empty."""
    loaded = runtime_files(running_root)
    c = compare(running_root, campaign_tree, loaded)
    return {"runtime_files": len(loaded), "runtime_not_in_static": sorted(set(loaded) - set(static)),
            "runtime_differ": c["differ"] + c["missing"]}


def run_record_commits(run_records: Path) -> dict[str, int]:
    """The harness commit of each run record in the pipeline's run_records.jsonl, counted. A record with none counts under "none"."""
    out: dict[str, int] = {}
    import json
    for line in Path(run_records).read_text().splitlines():
        if line.strip():
            c = json.loads(line).get("harness_commit") or "none"
            out[c] = out.get(c, 0) + 1
    return dict(sorted(out.items()))
