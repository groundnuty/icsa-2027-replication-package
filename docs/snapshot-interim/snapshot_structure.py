"""STRUCTURE ONLY of a snapshot's outputs: file names and column names (CSV header line), JSON key paths with every leaf replaced by its type. No row, no cell value, no count.
    python snapshot_structure.py <seal dir> > structure.md
"""
import csv, io, json, os, sys
from pathlib import Path

DIMS = ("block", "option", "layout", "model", "seed", "instance", "run", "cell", "contrast", "level", "provider", "backend", "record", "condition", "cause", "slot", "kind")

def header(path):
    with open(path, "r") as fh:
        first = fh.readline()
        if not first.startswith("# snapshot"):
            hdr = first
        else:
            hdr = fh.readline()
    return next(csv.reader(io.StringIO(hdr))) if hdr.strip() else []

def shape(x, depth=0, maxd=5):
    if isinstance(x, dict):
        if depth >= maxd:
            return "{...}"
        keys = list(x)
        # a dict keyed by cells / runs / blocks: show ONE example key pattern, not the values
        data_keyed = len(keys) > 12 and any(("__" in k) or ("|" in k) or ("/" in k) for k in keys)
        if data_keyed:           # a dict keyed by runs, cells, files: no key, no count; a cell key is a design name (option|layout|model), a run key is never shown
            import re
            tag = "<cell key: option|layout|model>" if all(re.fullmatch(r"[^|]+\|[^|]+\|[^|]+", k) for k in keys) else "<many keys>"
            return {tag: shape(x[keys[0]], depth + 1, maxd)}
        return {k: shape(v, depth + 1, maxd) for k, v in x.items()}
    if isinstance(x, list):
        return [shape(x[0], depth + 1, maxd)] if x else []
    return type(x).__name__

def main(seal):
    seal = Path(seal)
    print(f"# Structure of {seal.name} (names only: no value, no count)\n")
    tdir = seal / "out" / "tables"
    print(f"## Analysis tables: `{tdir}`\n\nEach `.csv` has a first line `# snapshot final=<true|false> t=<t>`, then the header, then rows (read with `pd.read_csv(path, skiprows=1)`). Each has a `.md` twin.\n")
    print("| table | columns | dimensions in the columns |\n|---|---|---|")
    for f in sorted(tdir.glob("*.csv")):
        cols = header(f)
        dims = [d for d in DIMS if d in cols]
        flag = " **(option x layout x model)**" if {"option", "layout", "model"} <= set(cols) else ""
        print(f"| {f.name} | {', '.join(cols) if cols else '(no columns when empty)'} | {', '.join(dims) or '-'}{flag} |")
    others = [f.name for f in sorted(tdir.iterdir()) if f.suffix not in (".csv", ".md")]
    print(f"\nOther files in tables/: {', '.join(others)}\n")
    for rel in ("out/pipeline/infra.json", "out/pipeline/none_counts.json", "out/pipeline/manifest.json", "h3/measure/counts.json", "h3/measure/self_report.json", "h3/measure/record.json", "out/tables/manifest.json"):
        p = seal / rel
        if p.is_file():
            try:
                print(f"## `{rel}` (keys; leaves are types)\n```json\n{json.dumps(shape(json.loads(p.read_text())), indent=1)[:6000]}\n```\n")
            except Exception as e:
                print(f"## `{rel}`: unreadable ({type(e).__name__})\n")
    for rel in ("h3/measure/record.csv", "out/pipeline/causes.csv", "out/pipeline/cause_flags.csv"):
        p = seal / rel
        if p.is_file():
            cols = header(p) if not open(p).readline().startswith("# snapshot") else header(p)
            print(f"## `{rel}`: columns {', '.join(cols)}\n")
    for rel in ("out/pipeline/scored_rows.jsonl", "out/pipeline/run_labels.jsonl", "out/pipeline/run_records.jsonl", "h3/platform_rows.jsonl"):
        p = seal / rel
        if p.is_file():
            with open(p) as fh:
                line = fh.readline()
            print(f"## `{rel}`: one JSON object per run; its keys (leaves are types)\n```json\n{json.dumps(shape(json.loads(line), 0, 3), indent=1)[:2500]}\n```\n")

def layout_section(seal):
    """lane-layout's stage (#34): every CSV under layout/ with its header, every small JSON as key paths with types, and DEFINITIONS.md verbatim (static text, no value). A file that cannot be
    read is named, never skipped silently."""
    seal = Path(seal)
    root = seal / "layout"
    if not root.is_dir():
        return
    print("## `layout/` (lane-layout's stage)\n")
    for f in sorted(root.rglob("*.csv")):
        try:
            cols = header(f)
            print(f"- `{f.relative_to(seal)}`: columns {', '.join(cols)}")
        except Exception as e:
            print(f"- `{f.relative_to(seal)}`: unreadable header ({type(e).__name__})")
    for f in sorted(root.rglob("*.json")):
        try:
            if f.stat().st_size > 2_000_000:
                print(f"- `{f.relative_to(seal)}`: JSON, {f.stat().st_size} bytes (not described)")
                continue
            print(f"- `{f.relative_to(seal)}`: keys {json.dumps(shape(json.loads(f.read_text()), 0, 3))[:700]}")
        except Exception as e:
            print(f"- `{f.relative_to(seal)}`: unreadable ({type(e).__name__})")
    d = root / "DEFINITIONS.md"
    if d.is_file():
        print("\n### layout/DEFINITIONS.md (verbatim)\n\n" + d.read_text())
    print()


main(sys.argv[1])
layout_section(sys.argv[1])
