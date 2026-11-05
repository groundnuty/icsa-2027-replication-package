"""The second-coder sample and the blind coding sheet.

Stratified 20% sample by option x layout x primary code (largest-remainder allocation, at
least one run per stratum, so the realised share is >= 20%). The sheet shows what the rule
coder read (traces, extents, listing) and hides what it produced: no code, no secondary, no
attribution, no stratum column, rows in shuffled order under opaque ids. The id -> run map
is a separate file (`key.csv`) that stays with the first coder.
"""
from __future__ import annotations

import hashlib
import math
import shutil
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

from . import codebook as cb
from .. import grid
from .batch import Batch
from .evidence import RunEvidence
from .rules import missing_cell_counts

SHEET_COLUMNS = [
    "sheet_id", "option", "layout", "termination", "error_type", "infra_failure", "infra_reason",
    "malformed_tool_call_rounds", "instrument_label", "report_complete_claim", "caveats",
    "analysed_share_baseline", "analysed_share_target", "read_share_baseline", "read_share_target",
    "analysed_cells_missing_every_day", "analysed_cells_missing_some_days",
    "read_beyond_units", "read_beyond_days", "read_other_days", "listing", "listing_disagrees", "truncated_downloads", "transcript_path",
    "code_cells_path",
    "coder_primary", "coder_secondary", "coder_notes"]
KEY_COLUMNS = ["sheet_id", "block", "run_key", "option", "layout"]


def sample_keys(batch: Batch, fraction: float = 0.2, seed: int = 0) -> list[tuple[str, str]]:
    strata: dict[tuple, list[tuple[str, str]]] = defaultdict(list)
    for c in batch.codings:
        ev = batch.evidence[(c.block, c.run_key)]
        strata[(ev.option.value, ev.layout.value, c.primary)].append((c.block, c.run_key))
    names = sorted(strata)
    n = len(names)
    quota = np.array([fraction * len(strata[s]) for s in names])
    take = np.floor(quota).astype(int)
    rng = np.random.default_rng(seed)
    target = int(round(quota.sum()))
    frac = quota - take
    order = sorted(range(n), key=lambda i: (-frac[i], rng.random()))
    for i in order:
        if take.sum() >= target:
            break
        take[i] += 1
    take = np.maximum(take, 1)
    out = []
    for s, k in zip(names, take):
        members = sorted(strata[s])
        pick = rng.choice(len(members), size=min(int(k), len(members)), replace=False)
        out += [members[i] for i in sorted(pick)]
    return sorted(out)


def _share(ext, req) -> float | str:
    if ext is None:
        return "not observed"
    r = req.count()
    return float("nan") if r == 0 else round(req.intersection(ext).count() / r, 4)


def _listing_text(listing) -> str:
    if listing is None:
        return "not observed"
    parts = []
    for d, v in sorted(listing.items()):
        parts.append(f"{d}: {v['entries_listed']} of {v['dir_size']} entries listed, "
                     f"complete={v['complete']}, truncated={v['truncated']}, "
                     f"requests={v.get('requests')}, with_token={v.get('requests_with_token')}, "
                     f"unused_continuations={v.get('unused_continuations')}")
    return " || ".join(parts) or "no listing requests"


def _days_text(days) -> str:
    """The rule compares these with the entries listed, so the coder needs their positions, not just how many."""
    if days is None:
        return "not observed"
    if not days:
        return "none"
    a, z = min(int(d) for d in days), max(int(d) for d in days)
    return f"{len(days)} days, {grid.day_date(a)} to {grid.day_date(z)} (positions {a} to {z} in the S1 directory)"


def sheet_id(seed: int, block: str, run_key: str) -> str:
    return hashlib.sha256(f"{seed}|{block}|{run_key}".encode()).hexdigest()[:10]


def sheet_row(ev: RunEvidence, sid: str) -> dict:
    # counts, not the extents: the same cell missing every day and a rotating cell read alike in the shares (b3 #4)
    every, some = ("not observed", "not observed") if ev.analysed is None else missing_cell_counts(ev.required, ev.analysed)
    return {
        "sheet_id": sid, "option": ev.option.value, "layout": ev.layout.value,
        "termination": ev.termination.value, "error_type": ev.error_type or "",
        "infra_failure": ev.infra_failure, "infra_reason": ev.infra_reason or "",
        "malformed_tool_call_rounds": ev.invalid_tool_args_rounds,
        "instrument_label": "" if ev.label is None else ev.label.value,
        "report_complete_claim": "" if ev.self_report_complete is None else ev.self_report_complete,
        "caveats": ev.caveats or "",
        "analysed_share_baseline": _share(ev.analysed.baseline if ev.analysed else None, ev.required.baseline),
        "analysed_share_target": _share(ev.analysed.target if ev.analysed else None, ev.required.target),
        "analysed_cells_missing_every_day": every, "analysed_cells_missing_some_days": some,
        "read_share_baseline": _share(ev.read.baseline if ev.read else None, ev.required.baseline),
        "read_share_target": _share(ev.read.target if ev.read else None, ev.required.target),
        "read_beyond_units": "not observed" if ev.read_beyond_units is None else ev.read_beyond_units,
        "read_beyond_days": _days_text(ev.read_beyond_days),
        "read_other_days": "not observed" if ev.read_other_days is None else len(ev.read_other_days),
        "listing": _listing_text(ev.listing),
        "listing_disagrees": "not observed" if ev.listing_disagrees is None else ev.listing_disagrees,
        "truncated_downloads": "not observed" if ev.truncated_downloads is None else ev.truncated_downloads,
        "transcript_path": ev.trace_paths.get("transcript", ""),
        "code_cells_path": ev.trace_paths.get("code_cells", ""),
        "coder_primary": "", "coder_secondary": "", "coder_notes": ""}


def _copy_run_files(run_dir: Path, row: dict, to: Path) -> dict:
    """The coder reads the run itself. Its directory's name holds the run key, so the files go under the sheet's opaque id;
    a path in the row is then relative to the sheet, or empty if the run has no such file."""
    to.mkdir(parents=True, exist_ok=True)
    out = {}
    for col, name in (("transcript_path", "transcript"), ("code_cells_path", "code_cells")):
        src = run_dir / str(row[col])
        out[col] = ""
        if row[col] and src.is_file():
            # named for the column, as two sources can share a name; of the source's name only a known suffix, as the name may hold the run key
            dst = to / (name + (src.suffix if src.suffix in (".json", ".jsonl") else ""))
            shutil.copyfile(src, dst)
            out[col] = dst.relative_to(to.parents[1]).as_posix()
    return out


def write_sheet(batch: Batch, out_dir: str | Path, fraction: float = 0.2, seed: int = 0, *,
                rows: dict[tuple[str, str], dict] | None = None, run_dirs: dict[tuple[str, str], Path] | None = None) -> dict:
    """`sheet.csv` + `codebook.md` go to the second coder; `key.csv` stays with the first. `rows`: the sampled runs' rows, if
    `batch`'s evidence no longer holds its extents (the pipeline's does not). `run_dirs`: where each run's files are; each sampled
    run's transcript and code then go under `files/<sheet id>/` beside the sheet."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    keys = sample_keys(batch, fraction, seed)
    rng = np.random.default_rng(seed + 1)
    shuffled = [keys[i] for i in rng.permutation(len(keys))]
    rows_in, sheet, key_rows = rows, [], []
    for block, run_key in shuffled:
        ev = batch.evidence[(block, run_key)]
        sid = sheet_id(seed, block, run_key)
        row = {**rows_in[(block, run_key)], "sheet_id": sid} if rows_in is not None else sheet_row(ev, sid)
        if run_dirs is not None:
            row.update(_copy_run_files(Path(run_dirs[(block, run_key)]), row, out / "files" / sid))
        sheet.append(row)
        key_rows.append({"sheet_id": sid, "block": block, "run_key": run_key,
                         "option": ev.option.value, "layout": ev.layout.value})
    pd.DataFrame(sheet, columns=SHEET_COLUMNS).to_csv(out / "sheet.csv", index=False)
    pd.DataFrame(key_rows, columns=KEY_COLUMNS).to_csv(out / "key.csv", index=False)
    (out / "codebook.md").write_text(cb.codebook_markdown())
    return {"n_coded": len(batch.codings), "n_sampled": len(keys), "share": len(keys) / max(1, len(batch.codings))}


def model_coder_prompt(row: dict, codebook_md: str) -> str:
    """The prompt for a model second coder: one sheet row plus the codebook, nothing else."""
    body = "\n".join(f"{k}: {row[k]}" for k in SHEET_COLUMNS if not k.startswith("coder_") and row.get(k) != "")
    return (f"{codebook_md}\n\nCode this run. Answer with `primary: <code>` and, if any, "
            f"`secondary: <code>;<code>`.\n\n{body}\n")
