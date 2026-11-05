"""Rubric §5: the decision rule for one packet, from the instrument label and both coders' verdicts.

- A coder's verdict is COMPLETE, OMITTING or CANNOT_TELL (compare.py), or MALFORMED when its
  answer never validated within the retry budget. MALFORMED is no verdict: it never agrees.
- The pair: COMPLETE if both are COMPLETE, OMITTING if both are OMITTING, otherwise none.
- An instrument `complete` or `omitting` STANDS, whatever the coders say (inspection never
  overrides the instrument). Only an instrument `unknown` is resolved: to `complete` when the
  pair is COMPLETE, to `omitting` when the pair is OMITTING (even if they name different parts),
  and it stays `unknown` otherwise.
- The counterfactual decomposition of a resolved `omitting` run is computable only when both
  coders' extractions agree EXACTLY (compare.py's `extraction_sha256` of the whole canonical
  extraction, so they also agree on what lies outside the required extent) and neither leaves any
  part CANNOT TELL (`exact`); otherwise it is reported as not computable for that run.
"""
from __future__ import annotations

CODER_VERDICTS = ("COMPLETE", "OMITTING", "CANNOT_TELL", "MALFORMED")
LABELS = ("complete", "omitting", "unknown")


def pair(v1: str, v2: str) -> str | None:
    for v in (v1, v2):
        if v not in CODER_VERDICTS:
            raise ValueError(f"not a coder verdict: {v!r}")
    if v1 == v2 and v1 in ("COMPLETE", "OMITTING"):
        return v1
    return None


def decomposition(d1: dict | None, d2: dict | None) -> dict:
    """Whether the decomposition is computable: d1, d2 are the coders' compare.Verdict.to_dict()."""
    if not d1 or not d2:
        return {"computable": False, "why": "a coder gave no valid answer"}
    if not (d1.get("exact") and d2.get("exact")):
        return {"computable": False, "why": "an extraction leaves a part CANNOT TELL or names cells by a rule"}
    if not d1.get("extraction_sha256") or d1.get("extraction_sha256") != d2.get("extraction_sha256"):
        return {"computable": False, "why": "the extractions differ"}
    return {"computable": True, "missing_extent_sha256": d1["missing_extent_sha256"],
            "missing_cell_days": d1.get("missing_cell_days")}


def decide(instrument_label: str, v1: str, v2: str, d1: dict | None = None, d2: dict | None = None) -> dict:
    """The final label of a run and how it was reached. d1, d2: the coders' compare verdict dicts
    (needed only for the decomposition of a resolved omitting run)."""
    if instrument_label not in LABELS:
        raise ValueError(f"not an instrument label: {instrument_label!r}")
    p = pair(v1, v2)
    out = {"instrument": instrument_label, "coders": [v1, v2], "pair": p}
    if instrument_label != "unknown":
        out.update(label=instrument_label, route="instrument", decomposition=None)
    elif p == "COMPLETE":
        out.update(label="complete", route="inspection", decomposition=None)
    elif p == "OMITTING":
        out.update(label="omitting", route="inspection", decomposition=decomposition(d1, d2))
    else:
        out.update(label="unknown", route="unresolved", decomposition=None)
    return out
