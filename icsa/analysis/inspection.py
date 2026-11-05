"""The coders' decisions into the analysis (amendment 11, rubric §8, amendment 19(a) and (f); #14).

H1's primary labels are those after inspection; the instrument-only labels (`ScoredRow.label_raw`) are a sensitivity row.
Inspection resolves only a run the instrument left `unknown` (icsa.inspection.decide): it never overrides `complete` or
`omitting`. Two inputs, keyed the same way, by (block, RunId.key()):

- **labels** (JSONL, one record per inspected run): `block`, `run_key`, `label_after_inspection` (complete | omitting | unknown),
  `route` (inspection | unresolved), and `coder_pair` where the decisions name one (amendment 26(j): `sol+opus` or `opus+sonnet`; absent in an
  older decisions file). Made from the inspection's `decisions.json` by `labels_from_decisions` (or
  `python -m icsa.analysis.inspection --decisions decisions.json --out labels.jsonl`). An empty file says inspection was not run.
- **coverage** (JSONL, optional): `block`, `run_key`, `both_agree_exactly`, `coverage_baseline`, `coverage_target`, the coders'
  extraction where both agree exactly (19(f)), and `coder_pair` (the coverage reader ignores it); see `adapter.apply_inspection_coverage`.
  Every coverage record needs a label record.

**Key contract with the inspection population** (icsa.inspection.queue): a population row's `run_key` is the campaign store's
run key, `<block>__<RunId.key()>` (a pilot run and the main run of the same cell share `RunId.key()`, and the queue keys on
`run_key` alone), and its `phase` is that block. `labels_from_decisions` refuses any other shape.

`label` stays the instrument's label after routing; the analysis reads the primary label through `adapter.primary_label`, the
coverage null rule through the instrument's label, and the routed share through the raw label and its reasons.
"""
from __future__ import annotations

import argparse
import collections
import dataclasses
import hashlib
import json
import pathlib
from typing import Iterable

from icsa.analysis import adapter
from icsa.records import OmissionLabel, ScoredRow

FORMAT_DECISIONS = "icsa-inspection-decisions-v1"      # icsa.inspection.report.FORMAT_DECISIONS
LABELS = ("complete", "omitting", "unknown")
PAIRS = ("sol+opus", "opus+sonnet")                    # icsa.inspection.plan.PAIR_NAMES, the names the decisions and coverage records carry
SOL_PARTS = frozenset({"sol", "codex"})                # a pair's parts: its name is `sol+opus`; coverage.py falls back to `codex+claude`
ROUTES = {"complete": "inspection", "omitting": "inspection", "unknown": "unresolved"}


@dataclasses.dataclass(frozen=True)
class InspectionInput:
    labels: tuple[dict, ...] = ()
    coverage: tuple[dict, ...] = ()
    source: str = "not run"

    @classmethod
    def not_run(cls) -> "InspectionInput":
        """The explicit statement that no inspection decision exists yet: every instrument `unknown` stays unknown, and the manifest
        counts them as not inspected."""
        return cls()

    @property
    def ran(self) -> bool:
        return bool(self.labels)


def _jsonl(path) -> tuple[list[dict], str]:
    raw = pathlib.Path(path).read_bytes()
    return [json.loads(x) for x in raw.decode().splitlines() if x.strip()], hashlib.sha256(raw).hexdigest()


def load(labels_path, coverage_path=None) -> InspectionInput:
    labels, sha = _jsonl(labels_path)
    cov, csha = _jsonl(coverage_path) if coverage_path else ([], None)
    src = f"labels:{pathlib.Path(labels_path).name}@{sha[:12]}" + (f";coverage:{pathlib.Path(coverage_path).name}@{csha[:12]}" if csha else "")
    return InspectionInput(tuple(labels), tuple(cov), src if labels or cov else "not run (explicit empty input)")


def coerce(inspection) -> InspectionInput:
    if inspection is None:
        raise ValueError("the inspection input is required: pass the coders' decisions (icsa.analysis.inspection.load / "
                         "labels_from_decisions) or InspectionInput.not_run() to state that inspection has not run")
    if isinstance(inspection, InspectionInput):
        return inspection
    raise TypeError(f"inspection must be an InspectionInput, not {type(inspection).__name__}")


def _key_of(run_key: str, phase: str) -> str:
    prefix = f"{phase}__"
    if not isinstance(run_key, str) or not run_key.startswith(prefix):
        raise ValueError(f"inspection decision for {run_key!r}: its run_key must be the store's <block>__<RunId.key()> with the block "
                         f"equal to its phase {phase!r}")
    key = run_key[len(prefix):]
    adapter.run_id_from_key(key)            # raises on anything that is not a run key
    return key


def labels_from_decisions(d: dict) -> list[dict]:
    """One label record per decided R-set packet (runs the instrument labelled `unknown`). K-test packets are not campaign runs and C-set
    packets are instrument-decided (inspection cannot change them), so neither gives a record; a packet still pending gives none either,
    and its run stays unknown, counted as not inspected."""
    if not isinstance(d, dict) or d.get("format") != FORMAT_DECISIONS or not isinstance(d.get("packets"), dict):
        raise ValueError(f"not an inspection decisions record: format must be {FORMAT_DECISIONS!r} with a 'packets' map")
    out, seen = [], set()
    for pid in sorted(d["packets"]):
        p = d["packets"][pid]
        if p.get("set") != "R" or p.get("decision") is None:
            continue
        dec = p["decision"]
        if p.get("instrument") != "unknown" or dec.get("instrument") != "unknown":
            raise ValueError(f"packet {pid}: an R-set decision on a run the instrument did not leave unknown ({p.get('instrument')!r})")
        if dec.get("label") not in LABELS or dec.get("route") != ROUTES[dec["label"]]:
            raise ValueError(f"packet {pid}: decision {dec.get('label')!r} by route {dec.get('route')!r} is not a decision of rubric §5")
        block = p.get("phase")
        key = _key_of(p.get("run_key"), block)
        if (block, key) in seen:
            raise ValueError(f"two decisions for run ({block}, {key})")
        seen.add((block, key))
        rec = {"block": block, "run_key": key, "label_after_inspection": dec["label"], "route": dec["route"]}
        pair = p.get("coder_pair")                  # amendment 26(j): the pair that coded this packet; an older decisions file has none
        if pair is not None:
            if not isinstance(pair, str) or not pair:
                raise ValueError(f"packet {pid}: coder_pair {pair!r} is not a pair name")
            rec["coder_pair"] = pair
        out.append(rec)
    return out


def apply(rows: Iterable[ScoredRow], inspection: InspectionInput) -> list[ScoredRow]:
    """The rows with `label_after_inspection` set from the label records, then the coders' coverage from the coverage records.
    Refused: a record for no scored run, two records for one run, a label for a run not finished, a label on a run the instrument did not
    leave `unknown` (inspection never overrides the instrument), a coverage record with no label record, a coverage record whose
    `coder_pair` differs from its label record's, and an exact coverage agreement on a run inspection left unknown (identical exact
    extractions give one verdict, so the pair resolves). The label record's `coder_pair` goes onto the row (None where it names none).
    A decided packet whose pair plan left it uncoded (`not_coded`) has no label record: its run stays as the instrument left it."""
    rows = list(rows)
    by = {(r.block, r.run.key()): k for k, r in enumerate(rows)}
    labelled: dict[tuple, str] = {}
    pairs: dict[tuple, str | None] = {}
    for e in inspection.labels:
        key = (e.get("block"), e.get("run_key"))
        if key not in by:
            raise ValueError(f"an inspection label for no scored run: {key}")
        if key in labelled:
            raise ValueError(f"two inspection labels for run {key}")
        lab = e.get("label_after_inspection")
        if lab not in LABELS:
            raise ValueError(f"run {key}: label_after_inspection {lab!r} is not one of {LABELS}")
        r = rows[by[key]]
        if not r.finished or r.label is None:
            raise ValueError(f"run {key}: not finished, so it has no label for inspection to resolve")
        if r.label is not OmissionLabel.UNKNOWN:
            raise ValueError(f"run {key}: inspection cannot override the instrument's {r.label.value}")
        pair = e.get("coder_pair")
        if pair is not None and (not isinstance(pair, str) or not pair):
            raise ValueError(f"run {key}: coder_pair {pair!r} is not a pair name")
        labelled[key], pairs[key] = lab, pair
        rows[by[key]] = dataclasses.replace(r, label_after_inspection=OmissionLabel(lab), coder_pair=pair)
    for e in inspection.coverage:
        key = (e.get("block"), e.get("run_key"))
        if key in by and key not in labelled:
            raise ValueError(f"run {key}: a coverage record from inspection with no inspection label for the run (both are keyed alike)")
        if key in labelled and None not in (e.get("coder_pair"), pairs[key]) and e["coder_pair"] != pairs[key]:
            raise ValueError(f"run {key}: its coverage record names the pair {e['coder_pair']!r}, its label record {pairs[key]!r}")
        if labelled.get(key) == "unknown" and e.get("both_agree_exactly") is True:
            raise ValueError(f"run {key}: the coders' extractions agree exactly, yet inspection left the run unknown")
    return adapter.apply_inspection_coverage(rows, list(inspection.coverage))   # checks the instrument's label, which stays unknown


def is_sol_coded(coder_pair) -> bool:
    """Amendment 26(j): the run was coded by the Opus + Sol pair, from its `coder_pair` name (`sol+opus`; `codex+claude` is read alike).
    **A record with no `coder_pair` is not Sol-coded for this purpose** (an older decisions file names no pair, and a guess would put
    runs into the sensitivity that the plan never showed Sol coded)."""
    return isinstance(coder_pair, str) and bool(SOL_PARTS & set(coder_pair.split("+")))


def sol_only(inspection: InspectionInput) -> InspectionInput:
    """Amendment 26(j)'s sensitivity row, "Sol-coded runs only": the label records of the Sol pair, and the coverage records of the
    runs they keep. **Both are filtered together by the run's key**, because `apply` refuses a coverage record with no label record. A run
    whose label record is dropped (the fallback pair coded it, or no pair is recorded) then has none, so it reads as not inspected and
    its instrument `unknown` stands: that is the sensitivity's meaning. A coverage record whose run has no label record at all is
    kept, so `apply` still refuses it. The primary analysis never reads this."""
    ins = coerce(inspection)
    kept = tuple(e for e in ins.labels if is_sol_coded(e.get("coder_pair")))
    dropped = {(e.get("block"), e.get("run_key")) for e in ins.labels} - {(e.get("block"), e.get("run_key")) for e in kept}
    cov = tuple(e for e in ins.coverage if (e.get("block"), e.get("run_key")) not in dropped)
    return InspectionInput(kept, cov, f"{ins.source};sol_only")


def pair_counts(rows: Iterable[ScoredRow], cfg=None) -> dict:
    """For the manifest (26(j): "every table marks" the pair): the runs each pair resolved, by the label after inspection, per pair and
    never pooled. A run with a label after inspection and no `coder_pair` is counted as `unrecorded`. With `cfg`, only the primary-scope
    runs (as `label_source_counts`). `complete` and `omitting` are runs the pair resolved, `unknown` those it left unknown."""
    rows = adapter.select_rows(rows, cfg)[0] if cfg is not None else list(rows)
    c: collections.Counter = collections.Counter(
        (r.coder_pair if r.coder_pair is not None else "unrecorded", r.label_after_inspection.value) for r in rows
        if r.label_after_inspection is not None)
    names = [*PAIRS, *sorted({p for p, _ in c} - set(PAIRS) - {"unrecorded"}), "unrecorded"]
    return {n: {**{lab: int(c.get((n, lab), 0)) for lab in LABELS}, "inspected": sum(int(c.get((n, lab), 0)) for lab in LABELS)}
            for n in names}


PAIR_HEADER = "Coder pairs (amendment 26(j))"        # the first words of the line `pair_header` gives, so a table that carries it can be recognised


def pair_header(rows: Iterable[ScoredRow], cfg, inspection: "InspectionInput") -> str:
    """One line for the head of an aggregate table (amendment 26(j): "every table marks" the pair): per pair, the runs it resolved and their share of the
    analysis's primary-scope runs, never pooled over the pairs. **The set is the analysis's selected rows, not the table's own runs** (a table does not
    carry its runs), and the line says so. With no inspection input, or no pair on any record, it says that instead of leaving the pair out."""
    kept, _ = adapter.select_rows(rows, cfg)
    n = len(kept)
    where = f"over the {n} primary-scope run(s) the analysis selects, not this table's own runs"
    if not coerce(inspection).ran:
        return f"{PAIR_HEADER}, {where}: no inspection input, so no run has a pair"
    counts = pair_counts(kept)
    if not any(c["inspected"] for name, c in counts.items() if name != "unrecorded"):
        return f"{PAIR_HEADER}, {where}: no pair is recorded on any inspected run ({counts['unrecorded']['inspected']} inspected run(s) name none)"
    share = lambda k: f"{k} ({k / n:.3g})"                   # n > 0 here: a run was inspected
    parts = [f"{'no pair on record' if name == 'unrecorded' else name} {share(c['inspected'])}" for name, c in counts.items()
             if name != "unrecorded" or c["inspected"]]
    return f"{PAIR_HEADER}, runs resolved per pair and their share, {where}: " + "; ".join(parts)


def label_source_counts(rows: Iterable[ScoredRow], cfg) -> dict:
    """Per primary-scope finished run: where its primary label comes from (adapter.LABEL_SOURCES), for the manifest."""
    kept, _ = adapter.select_rows(rows, cfg)
    c = collections.Counter(adapter.label_source(r) for r in kept)
    return {s: int(c.get(s, 0)) for s in adapter.LABEL_SOURCES}


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="decisions.json (icsa.inspection.report) -> the analysis's label records (JSONL)")
    ap.add_argument("--decisions", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    recs = labels_from_decisions(json.loads(pathlib.Path(a.decisions).read_text()))
    pathlib.Path(a.out).write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in recs))
    print(json.dumps({"records": len(recs), **collections.Counter(r["label_after_inspection"] for r in recs)}))


if __name__ == "__main__":
    main()
