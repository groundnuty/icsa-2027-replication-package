"""Code a set of runs and write the table #14 joins on (`--causes`): block, run_key, cause."""
from __future__ import annotations

import collections
import dataclasses
from collections.abc import Iterable

import pandas as pd

from .evidence import RunEvidence
from .rules import Coding, Skipped, code_run

FLAG_COLUMNS = ["block", "run_key", "option", "recovered_from_truncated_listing", "listing_evidence_incomplete",
                "listing_disagrees", "decoded_not_delivered", "delivered_not_decoded"]
COLUMNS = ["block", "run_key", "cause", "secondary", "attribution", "cause_detail", "population", "trail",
           "recovered_from_truncated_listing"]


@dataclasses.dataclass
class Batch:
    codings: list[Coding]
    skipped: list[Skipped]
    evidence: dict[tuple[str, str], RunEvidence]     # the attempt that was coded, by (block, run_key)

    def skipped_counts(self) -> dict[str, int]:
        """Runs left out of the coded population, by reason. `unknown_label` are the finished runs the
        instrument could not decide: counted and reported, never coded as a cause."""
        return dict(collections.Counter(s.reason for s in self.skipped))

    def breakdowns(self) -> dict[str, dict[str, int]]:
        """Primary-cause counts per population. `incorrect_complete` (complete extent, wrong result)
        is its own breakdown and is never merged with the omission causes."""
        out: dict[str, dict[str, int]] = {}
        for c in self.codings:
            d = out.setdefault(c.population, {})
            d[c.primary] = d.get(c.primary, 0) + 1
        return out

    def listing_evidence_incomplete_count(self) -> int:
        """Runs with a cut listing and reads outside the required days of unknown day: neither coded as
        truncated_listing nor counted as recovered. Named so they cannot vanish."""
        return sum(x.listing_evidence_incomplete for x in [*self.codings, *self.skipped])

    def listing_evidence_incomplete_by_option(self) -> dict[str, int]:
        """The same count per option (T, D, M); an option with none shows 0, so it cannot go missing."""
        out: dict[str, int] = {}
        for x in [*self.codings, *self.skipped]:
            o = self.evidence[(x.block, x.run_key)].option.value
            out[o] = out.get(o, 0) + int(x.listing_evidence_incomplete)
        return dict(sorted(out.items()))

    def listing_disagrees_by_option(self) -> dict[str, int]:
        """Runs whose tracer listing and gate /children requests disagree, per option (0 shown)."""
        out: dict[str, int] = {}
        for x in [*self.codings, *self.skipped]:
            ev = self.evidence[(x.block, x.run_key)]
            out[ev.option.value] = out.get(ev.option.value, 0) + int(bool(ev.listing_disagrees))
        return dict(sorted(out.items()))

    def flags_table(self) -> pd.DataFrame:
        """The recovery flag for every run of the batch: coded, skipped and complete ones alike."""
        rows = [{"block": x.block, "run_key": x.run_key,
                 "option": self.evidence[(x.block, x.run_key)].option.value,
                 "recovered_from_truncated_listing": x.recovered_from_truncated_listing,
                 "listing_evidence_incomplete": x.listing_evidence_incomplete,
                 "listing_disagrees": self.evidence[(x.block, x.run_key)].listing_disagrees,
                 "decoded_not_delivered": self.evidence[(x.block, x.run_key)].decoded_not_delivered,
                 "delivered_not_decoded": self.evidence[(x.block, x.run_key)].delivered_not_decoded}
                for x in sorted([*self.codings, *self.skipped], key=lambda x: (x.block, x.run_key))]
        return pd.DataFrame(rows, columns=FLAG_COLUMNS)

    def table(self) -> pd.DataFrame:
        rows = [{"block": c.block, "run_key": c.run_key, "cause": c.primary,
                 "secondary": ";".join(c.secondary), "attribution": c.attribution or "",
                 "cause_detail": c.cause_detail, "population": c.population, "trail": " | ".join(c.trail),
                 "recovered_from_truncated_listing": c.recovered_from_truncated_listing}
                for c in self.codings]
        return pd.DataFrame(rows, columns=COLUMNS)


def code_runs(evs: Iterable[RunEvidence]) -> Batch:
    """One coding per (block, run_key): the last attempt (infra retries share a run_key). Two
    records of the same attempt are an error, as #14 refuses duplicates."""
    last: dict[tuple[str, str], RunEvidence] = {}
    for ev in evs:
        k = (ev.block, ev.run_key)
        if k in last and last[k].attempt == ev.attempt:
            raise ValueError(f"duplicate evidence for {k} attempt {ev.attempt}")
        if k not in last or ev.attempt > last[k].attempt:
            last[k] = ev
    codings, skipped = [], []
    for k in sorted(last):
        r = code_run(last[k])
        (codings if isinstance(r, Coding) else skipped).append(r)
    return Batch(codings, skipped, last)
