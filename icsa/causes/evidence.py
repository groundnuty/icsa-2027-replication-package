"""What the rule coder reads about one run. A plain struct: the coder never opens a trace.

Built from the #8 RunRecord, the #13 ScoredRow, the required extent (#5) and the #9 labeller
summary. #9's modules are not imported (they may not be on the branch); the listing summary
is read in its `DirListing.to_json` shape: path, requests, requests_with_token, pages_seen,
entries_listed, complete, truncated, unused_continuations, attribution, dir_size,
failed_requests.
"""
from __future__ import annotations

import dataclasses
import json
from collections.abc import Iterable
from pathlib import Path

from icsa.extent import Extent, PartedExtent
from icsa.records import Layout, OmissionLabel, Option, RunRecord, ScoredRow, Termination

LISTING_KEYS = ("path", "entries_listed", "complete", "truncated", "attribution", "dir_size")


@dataclasses.dataclass
class RunEvidence:
    block: str | None
    run_key: str
    option: Option
    layout: Layout
    termination: Termination
    finished: bool
    label: OmissionLabel | None            # #9; None if not finished
    required: PartedExtent
    analysed: PartedExtent | None = None   # A_lo; None: no extent recorded
    read: PartedExtent | None = None       # None: not observed (never "empty")
    listing: dict[str, dict] | None = None  # per directory, DirListing.to_json; None: not observed
    truncated_downloads: int | None = None  # None: not observed
    read_beyond_units: int | None = None   # units the run read outside the required set (ReadExtent.beyond)
    read_beyond_days: list[int] | None = None  # day indices of the reads outside the required set; None: not given
    read_other_days: list[int] | None = None   # ReadExtent.other_days: other dates decoded, in either layout; None: not given
    listing_disagrees: bool | None = None  # #9: tracer and gate count /children requests differently; None: no gate view
    infra_failure: bool = False
    infra_reason: str | None = None
    attempt: int = 1
    invalid_tool_args_rounds: int = 0
    correct: bool | None = None
    complete_extent: bool | None = None
    cf_computation_f1: float | None = None
    self_report_complete: bool | None = None
    caveats: str | None = None             # report.json caveats, for the second coder only
    error_type: str | None = None
    # #9's cross-checks (additive; None: not observed). Neither ever changes a label.
    decoded_not_delivered: bool | None = None
    delivered_not_decoded: bool | None = None
    trace_paths: dict[str, str] = dataclasses.field(default_factory=dict)  # transcript, code cells: for the sheet

    def __post_init__(self) -> None:
        if self.block is None:
            raise ValueError(f"run {self.run_key}: no block; a cause row cannot be placed (see #14)")
        if self.listing is not None:
            for d, v in self.listing.items():
                miss = [k for k in LISTING_KEYS if k not in v]
                if miss:
                    raise ValueError(f"run {self.run_key}: listing {d!r} lacks {miss}")


def evidence_from(record: RunRecord, scored: ScoredRow, required: PartedExtent, *,
                  analysed: PartedExtent | None, read: PartedExtent | None,
                  listing: dict[str, dict] | None = None, truncated_downloads: int | None = None,
                  read_beyond_units: int | None = None, read_beyond_days: Iterable[int] | None = None,
                  read_other_days: Iterable[int] | None = None, caveats: str | None = None, listing_disagrees: bool | None,
                  decoded_not_delivered: bool | None = None, delivered_not_decoded: bool | None = None) -> RunEvidence:
    """The record and the scored row must be the same run and block. `listing_disagrees` has no default: it gates
    truncated_listing, so a caller that forgets it must fail, not code a disputed listing (science, #9, 1 Nov 23:26Z)."""
    if record.run != scored.run:
        raise ValueError(f"record {record.run.key()} and scored row {scored.run.key()} differ")
    if record.block != scored.block:
        raise ValueError(f"run {record.run.key()}: block {record.block!r} vs {scored.block!r}")
    return RunEvidence(
        block=record.block, run_key=record.run.key(), option=record.run.option, layout=record.run.layout,
        termination=record.termination, finished=scored.finished, label=scored.label,
        required=required, analysed=analysed, read=read, listing=listing,
        truncated_downloads=truncated_downloads, read_beyond_units=read_beyond_units,
        read_beyond_days=None if read_beyond_days is None else sorted(int(d) for d in read_beyond_days),
        read_other_days=None if read_other_days is None else sorted(int(d) for d in read_other_days),
        listing_disagrees=listing_disagrees, infra_failure=record.infra_failure,
        infra_reason=record.infra_reason, attempt=record.attempt,
        invalid_tool_args_rounds=record.invalid_tool_args_rounds, correct=scored.correct,
        complete_extent=scored.complete_extent, cf_computation_f1=scored.cf_computation_f1,
        self_report_complete=scored.self_report_complete, caveats=caveats, error_type=record.error_type,
        decoded_not_delivered=decoded_not_delivered,
        delivered_not_decoded=delivered_not_decoded,
        trace_paths={"transcript": record.transcript_path, "code_cells": record.code_cells_path})


def truncated_downloads(proxy_lines: Iterable[dict], file_sizes: dict[str, int]) -> int:
    """Whole-file downloads (a 200 content line, no range) that delivered fewer bytes than the
    file holds. `file_sizes`: dataset path -> size, from the layout index (not from the run).
    Only files in `file_sizes` count."""
    n = 0
    for e in proxy_lines:
        if e.get("kind") != "content" or e.get("method", "GET") == "HEAD":
            continue
        p = str(e.get("path", ""))
        if e.get("status") == 200 and e.get("range") is None and p in file_sizes \
                and e.get("bytes") is not None and e["bytes"] < file_sizes[p]:
            n += 1
    return n


# ---- JSON form, for the CLI: extents are saved next to the row ----

def _save_parted(pe: PartedExtent | None, stem: Path) -> str | None:
    if pe is None:
        return None
    pe.baseline.save(str(stem) + ".baseline.npz")
    pe.target.save(str(stem) + ".target.npz")
    return stem.name


def _load_parted(name: str | None, root: Path) -> PartedExtent | None:
    if name is None:
        return None
    s = root / name
    return PartedExtent(Extent.load(str(s) + ".baseline.npz"), Extent.load(str(s) + ".target.npz"))


def write_evidence(evs: Iterable[RunEvidence], root: str | Path) -> Path:
    """`<root>/evidence.jsonl` plus one set of .npz files per run and extent."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    with open(root / "evidence.jsonl", "w") as fh:
        for i, ev in enumerate(evs):
            d = {f.name: getattr(ev, f.name) for f in dataclasses.fields(ev)
                 if f.name not in ("required", "analysed", "read")}
            d["option"], d["layout"], d["termination"] = ev.option.value, ev.layout.value, ev.termination.value
            d["label"] = None if ev.label is None else ev.label.value
            for k in ("required", "analysed", "read"):
                d[k] = _save_parted(getattr(ev, k), root / f"{i:06d}.{k}")
            fh.write(json.dumps(d, sort_keys=True) + "\n")
    return root / "evidence.jsonl"


def read_evidence(root: str | Path) -> list[RunEvidence]:
    root = Path(root)
    out = []
    for line in (root / "evidence.jsonl").read_text().splitlines():
        d = json.loads(line)
        d["option"], d["layout"] = Option(d["option"]), Layout(d["layout"])
        d["termination"] = Termination(d["termination"])
        d["label"] = None if d["label"] is None else OmissionLabel(d["label"])
        for k in ("required", "analysed", "read"):
            d[k] = _load_parted(d[k], root)
        out.append(RunEvidence(**d))
    return out
