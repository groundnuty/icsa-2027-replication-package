"""The second-coder sheet for the causes `snapshot.codercauses` gives (#34, science 5 Nov 12:19Z, item 8): the codebook's kappa needs a second author.

    python -m snapshot.codersheet <seal> --answers-root DIR --out DIR [--fraction 0.2] [--seed 0] [--code-column cause|cause_window_rule]

The design is the repository's own (`icsa.causes.sampling.write_sheet`, the same code the pipeline uses for its coded runs): a 20% sample stratified by option x layout x primary code (largest-remainder
allocation, at least one run per stratum, so the realised share is at least 20%); `sheet.csv` shows what the first coder read (shares of the required extent analysed, cell counts, the listing,
termination, the report's claim and caveats, the paths of the transcript and the code) and HIDES what it produced: no code, no secondary, no attribution, no stratum column; opaque ids (a hash of
seed|block|run), rows in shuffled order; `key.csv` (id -> run) stays with the first coder; each sampled run's transcript and code cells are copied under `files/<opaque id>/` (named for the
column, never the run key). `codebook.md` is the text of the codes. The pipeline's own sheet for the instrument-labelled and unfinished runs is `out/pipeline/second_coder` of the same seal;
this one is for the runs the coders resolved to omitting, with the same blinding, so the operator hands on both. The pipeline keeps no rows for its unsampled runs, so one joint re-sample is not possible.

`--code-column` is the code the strata and the key use: `cause` (the codebook, strictly) or `cause_window_rule` (a whole-day window shortfall counted as wrong_subset): science's choice; it is never in the sheet.
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import argparse    # noqa: E402
import csv         # noqa: E402
import dataclasses    # noqa: E402
import hashlib     # noqa: E402
import json        # noqa: E402
import os          # noqa: E402
import re          # noqa: E402
import shutil      # noqa: E402
import tomllib     # noqa: E402
from pathlib import Path    # noqa: E402

import numpy as np    # noqa: E402

from icsa.causes import codebook as CB    # noqa: E402
from icsa.causes.batch import Batch    # noqa: E402
from icsa.causes.sampling import SHEET_COLUMNS, sample_keys, sheet_row, write_sheet    # noqa: E402
from icsa.inspection import packet as PK, queue as QU    # noqa: E402

from . import coderreplay as CR    # noqa: E402
from . import codercauses as CC    # noqa: E402


def build(seal: Path, answers_root: Path, out: Path, *, fraction: float = 0.2, seed: int = 0, code_column: str = "cause", ext: CR.Extents | None = None) -> dict:
    if code_column not in ("cause", "cause_window_rule"):
        raise ValueError(f"code column {code_column!r}")
    runs_all = CC.coded_runs(seal, answers_root, ext)
    runs = [r for r in runs_all if r["coding"] is not None]
    codings, evidence, rows, run_dirs = [], {}, {}, {}
    for r in runs:
        c, key = r["coding"], (r["coding"].block, r["coding"].run_key)
        if code_column == "cause_window_rule":
            c = dataclasses.replace(c, primary=r["row"]["cause_window_rule"])
        codings.append(c)
        evidence[key] = r["ev"]
        rows[key] = sheet_row(r["ev"], "")
        run_dirs[key] = Path(r["run_dir"])
    info = write_sheet(Batch(codings, [], evidence), Path(out), fraction, seed, rows=rows, run_dirs=run_dirs)
    meta = {**info, "fraction": fraction, "seed": seed, "code_column": code_column, "runs_without_a_cause": sum(1 for r in runs_all if r["coding"] is None)}
    (Path(out) / "SHEET.meta.json").write_text(json.dumps(meta, indent=1, sort_keys=True))
    os.chmod(Path(out) / "SHEET.meta.json", 0o600)
    return meta


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m snapshot.codersheet", description=__doc__.split("\n\n")[0])
    ap.add_argument("seal")
    ap.add_argument("--answers-root", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--fraction", type=float, default=0.2)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--code-column", default="cause", choices=["cause", "cause_window_rule"])
    ap.add_argument("--handoff", action="store_true", help="make the operator's hand-off folder (one merged sheet under one blinding, scanned) instead of the coder-derived sheet alone")
    a = ap.parse_args(argv)
    os.umask(0o077)
    out = Path(a.out)
    if a.handoff:
        try:
            r = handoff(Path(a.seal), Path(a.answers_root), out, fraction=a.fraction, seed=a.seed)
        except HandoffLeak as e:
            print(f"codersheet: the folder would carry what it must not ({e}); nothing put in place", file=sys.stderr)
            return 3
        except (OSError, ValueError, KeyError, CR.ReplayError) as e:
            print(f"codersheet refused: {type(e).__name__}: {getattr(e, 'reason', '') or str(e)[:120]}", file=sys.stderr)
            return 2
        print(json.dumps({"written": True, "rows": r["rows"]}))
        return 0
    if out.exists() and any(out.iterdir()):
        print(f"codersheet refused: {out} is not empty (a sheet is made once)", file=sys.stderr)
        return 2
    out.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        build(Path(a.seal), Path(a.answers_root), out, fraction=a.fraction, seed=a.seed, code_column=a.code_column)
    except (OSError, ValueError, KeyError, CR.ReplayError) as e:
        print(f"codersheet refused: {type(e).__name__}: {getattr(e, 'reason', '') or str(e)[:120]}", file=sys.stderr)
        return 2
    print(json.dumps({"written": True}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# ---------------------------------------------------------------------------------------------------------------------------------- the hand-off folder for the operator's second coders
# (science, #34 12:38Z): ONE folder, one merged sheet (the pipeline's rows and the coder-derived rows under one blinding), the files of each run, a blank answers file, the codebook. Not in it:
# key.csv, codes, labels, model names, run keys, the cut's totals; the folder is scanned for those (names and contents, transcripts and code cells included) before it is put in place.
READER_COLUMNS = ["sheet_id", "option", "layout", "termination", "error_type", "infra_failure", "infra_reason", "malformed_tool_call_rounds", "report_complete_claim", "caveats",
                  "analysed_share_baseline", "analysed_share_target", "analysed_cells_missing_every_day", "analysed_cells_missing_some_days",
                  "analysed_missing_baseline_days", "analysed_missing_baseline_ranges", "analysed_missing_target_days", "analysed_missing_target_ranges", "analysed_other_days",
                  "read_share_baseline", "read_share_target", "read_beyond_units", "read_beyond_days", "read_other_days", "listing", "listing_disagrees", "truncated_downloads",
                  "transcript_path", "code_cells_path"]
ANSWER_COLUMNS = ["sheet_id", "primary_code", "secondary_codes", "minutes"]
NOT_RECORDED = "not recorded"
TEXT_COLUMNS = ("error_type", "infra_reason", "caveats", "listing")
HANDOFF_SALT = "second-coder-handoff"
GENERIC_RUN_KEY = re.compile(r"\b[A-Za-z0-9]+__(?:T|T-unpaginated|D|M|M\+)__S[12]__[\w.-]+__s\d+\b")


class HandoffLeak(Exception):
    """The folder would carry something it must not; `args[0]` is a count by kind, never the thing."""


def model_names(extra=()) -> set:
    d = tomllib.load(open(CR.ROOT / "config" / "models.toml", "rb")).get("models", {})
    out = {str(x) for x in extra if x}
    for key, m in d.items():
        for v in (key, m.get("reported_name"), m.get("api_id"), str(m.get("api_id") or "").split("/")[-1], m.get("name")):
            if v and len(str(v)) >= 3:
                out.add(str(v))
    return out


def new_sheet_id(block, run_key) -> str:
    return hashlib.sha256(f"{HANDOFF_SALT}|{block}|{run_key}".encode()).hexdigest()[:10]


def _sanitiser(store_key, rec_key, instance_id, model, run_dir, instance_ids, models) -> PK.Sanitiser:
    return PK.Sanitiser(QU.identifiers({"run_key": store_key or rec_key, "key": rec_key, "instance_id": instance_id, "model": model, "run_dir": run_dir or ""},
                                       instance_ids=instance_ids, model_names=models))


def _clean_file(src: Path, dst: Path, san: PK.Sanitiser) -> str:
    """The run's file with identifiers, endpoints and credentials replaced by tokens; returns the relative name's suffix kept. A binary or unreadable file is not copied."""
    text = src.read_text(errors="replace")
    dst.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    dst.write_text(san(text))
    os.chmod(dst, 0o600)
    return dst.name


def _decoded_strings(text: str) -> str:
    """Every string (and key) of a JSON or JSON-lines document, decoded, one per line."""
    out: list[str] = []

    def walk(o):
        if isinstance(o, str):
            out.append(o)
        elif isinstance(o, dict):
            for k, v in o.items():
                out.append(str(k))
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    docs = [text] if "\n" not in text.strip() else text.splitlines()
    for d in docs + ([text] if len(docs) > 1 else []):
        try:
            walk(json.loads(d))
        except ValueError:
            continue
    return "\n".join(out)


def leak_scan(root: Path, *, keys: set, models: set, extra_names=()) -> dict:
    """Counts by kind of what must not be in the folder: model names, run keys (the given ones and anything shaped like one), code names, label records, key files. Names and contents."""
    code_names = [c for c in CB.CODE_NAMES if "_" in c]
    found = {"model_name": 0, "run_key": 0, "code_name": 0, "label_record": 0, "key_file": 0}
    low_models = [m.lower() for m in models if len(m) >= 3]
    for p in sorted(Path(root).rglob("*")):
        rel = p.relative_to(root).as_posix()
        text = rel + "\n" + (p.read_text(errors="replace") if p.is_file() else "")
        if p.name == "sheet.csv" and p.parent == Path(root):
            # the sheet's own columns are evidence the rules see, and their names and the termination values are code names by design (time_cap, infra_failure): they are the evidence, not a code
            rows = list(csv.reader(text.split("\n", 1)[1].splitlines()))
            head, body = rows[0], rows[1:]
            skip = {head.index("termination"), head.index("infra_failure")}
            text = rel + "\n" + "\n".join(",".join(c for k, c in enumerate(r) if k not in skip) for r in body)
        if p.is_file() and p.suffix in (".json", ".jsonl"):
            text += "\n" + _decoded_strings(p.read_text(errors="replace"))      # a JSON string's escapes (\\" and \\n) hide a record from a pattern; scan what the reader will read
        lower = text.lower()
        found["model_name"] += sum(lower.count(m) for m in low_models)
        found["run_key"] += sum(text.count(k) for k in keys if k) + len(GENERIC_RUN_KEY.findall(text))
        found["code_name"] += sum(lower.count(c) for c in code_names) if p.name != "codebook.md" else 0
        found["label_record"] += sum(len(rx.findall(text)) for rx, _ in PK.BLOCKING)
        if p.is_file() and (p.name.lower().startswith("key") or p.name.lower() in extra_names):
            found["key_file"] += 1
    return {k: v for k, v in found.items() if v}


def _days_cols(summary: dict | None) -> dict:
    if summary is None:
        return {c: NOT_RECORDED for c in ("analysed_missing_baseline_days", "analysed_missing_baseline_ranges", "analysed_missing_target_days", "analysed_missing_target_ranges", "analysed_other_days")}
    return {"analysed_missing_baseline_days": summary["missing_baseline_days"], "analysed_missing_baseline_ranges": summary["missing_baseline_ranges"],
            "analysed_missing_target_days": summary["missing_target_days"], "analysed_missing_target_ranges": summary["missing_target_ranges"], "analysed_other_days": summary["other_days"]}


def handoff(seal: Path, answers_root: Path, out: Path, *, pipeline_dir: Path | None = None, key_dir: Path | None = None, fraction: float = 0.2, seed: int = 0,
            ext: CR.Extents | None = None, pipeline_days=None) -> dict:
    """Builds the folder in `out`.building, scans it, and only then moves it to `out`. `key.csv` (new id -> run) goes to `key_dir` (default <seal>/coder_replay/second_coder_key), never to `out`.
    `pipeline_days(block, rec_key) -> summary dict | None`: the missing-day evidence of a pipeline-coded run, if it can be had (the pipeline keeps no extents)."""
    seal, out = Path(seal), Path(out)
    pipeline_dir = Path(pipeline_dir) if pipeline_dir else seal / "out" / "pipeline" / "second_coder"
    key_dir = Path(key_dir) if key_dir else seal / "coder_replay" / "second_coder_key"
    if out.exists():
        raise ValueError(f"{out} exists: a hand-off is made once")
    build_dir = out.with_name(out.name + ".building")
    if build_dir.exists():
        shutil.rmtree(build_dir)
    for d in (out.parent, build_dir, key_dir):
        d.mkdir(mode=0o700, parents=True, exist_ok=True)
    pop = CR._population(seal)
    pop_by_key = {(r.get("block"), r.get("key")): r for r in pop.values()}
    decisions = json.loads((seal / "inspection" / "decisions.json").read_text())
    models = model_names({p.get("model") for p in decisions["packets"].values()} | {r.get("model") for r in pop.values()})
    m, recs, _ = CR._manifest()
    instance_ids = sorted(recs)
    rows: list[dict] = []        # {"new": reader row, "key": (block, rec_key), "src": "pipeline"|"coder", "files": {col: (path, name)}, "san": Sanitiser}
    # the pipeline's own sample, as the pipeline drew it
    sheet_p, key_p = pipeline_dir / "sheet.csv", pipeline_dir / "key.csv"
    if sheet_p.is_file() and key_p.is_file():
        keys = {k["sheet_id"]: k for k in csv.DictReader(open(key_p))}
        for r in csv.DictReader(open(sheet_p)):
            k = keys[r["sheet_id"]]
            block, rec_key = k["block"], k["run_key"]
            iid, _, _, model = rec_key.split("__")[:4]
            row_pop = pop_by_key.get((block, rec_key), {})
            san = _sanitiser(row_pop.get("run_key") or f"{block}__{rec_key}", rec_key, iid, model, row_pop.get("run_dir"), instance_ids, models)
            rows.append({"r": r, "key": (block, rec_key), "src": "pipeline", "san": san, "days": pipeline_days(block, rec_key) if pipeline_days else None,
                         "files": {c: pipeline_dir / r[c] for c in ("transcript_path", "code_cells_path") if r.get(c)}, "option": k["option"], "layout": k["layout"]})
    # the coder-derived runs: the same sample, drawn from their causes
    runs_all = CC.coded_runs(seal, answers_root, ext)
    runs = [x for x in runs_all if x["coding"] is not None]
    if runs:
        codings = [x["coding"] for x in runs]
        evidence = {(x["coding"].block, x["coding"].run_key): x["ev"] for x in runs}
        take = set(sample_keys(Batch(codings, [], evidence), fraction, seed))
        for x in runs:
            key = (x["coding"].block, x["coding"].run_key)
            if key not in take:
                continue
            ev, rp = x["ev"], x["row"]
            r = sheet_row(ev, "")
            row_pop = pop_by_key.get(key, {})
            san = _sanitiser(row_pop.get("run_key"), key[1], rp["instance_id"], rp["model"], x["run_dir"], instance_ids, models)
            rd = Path(x["run_dir"])
            rows.append({"r": r, "key": key, "src": "coder", "san": san, "days": x["days"],
                         "files": {c: rd / r[c] for c in ("transcript_path", "code_cells_path") if r.get(c) and (rd / r[c]).is_file()}, "option": ev.option.value, "layout": ev.layout.value})
    # one blinding: new opaque ids, a shuffled order
    order = np.random.default_rng(seed + 1).permutation(len(rows))
    sheet, key_rows = [], []
    for i in order:
        x = rows[int(i)]
        sid = new_sheet_id(*x["key"])
        new = {c: x["r"].get(c, "") for c in READER_COLUMNS}
        new.update(_days_cols(x["days"]) if x["src"] == "coder" or x["days"] else _days_cols(None))
        for c in TEXT_COLUMNS:
            new[c] = x["san"](str(new[c])) if new[c] not in ("", None) else ""
        new["sheet_id"] = sid
        for col, src in x["files"].items():
            new[col] = ""
            if Path(src).is_file():
                suffix = ".jsonl" if str(src).endswith(".jsonl") else ".json"
                name = ("transcript" if col == "transcript_path" else "code_cells") + suffix
                _clean_file(Path(src), build_dir / "files" / sid / name, x["san"])
                new[col] = f"files/{sid}/{name}"
        for col in ("transcript_path", "code_cells_path"):
            new.setdefault(col, "")
            if col not in x["files"]:
                new[col] = ""
        sheet.append(new)
        key_rows.append({"sheet_id": sid, "block": x["key"][0], "run_key": x["key"][1], "source": x["src"], "option": x["option"], "layout": x["layout"]})
    with open(build_dir / "sheet.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, READER_COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(sheet)
    with open(build_dir / "answers.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, ANSWER_COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows({"sheet_id": r["sheet_id"]} for r in sheet)
    (build_dir / "codebook.md").write_text(CB.codebook_markdown())
    # the scan: nothing is put in place that carries what it must not
    forbidden_keys = {x["key"][1] for x in rows} | {f"{x['key'][0]}__{x['key'][1]}" for x in rows}
    leaks = leak_scan(build_dir, keys=forbidden_keys, models=models)
    for p in [build_dir, *build_dir.rglob("*")]:
        os.chmod(p, 0o700 if p.is_dir() else 0o600)
    with open(key_dir / "key.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, ["sheet_id", "block", "run_key", "source", "option", "layout"], lineterminator="\n")
        w.writeheader()
        w.writerows(key_rows)
    os.chmod(key_dir / "key.csv", 0o600)
    if leaks:
        raise HandoffLeak(json.dumps(leaks, sort_keys=True))
    os.replace(build_dir, out)
    return {"rows": len(sheet), "pipeline_rows": sum(1 for x in rows if x["src"] == "pipeline"), "coder_rows": sum(1 for x in rows if x["src"] == "coder")}
