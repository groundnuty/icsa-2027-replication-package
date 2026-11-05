"""Audit lines to runs, by (slot user, lease window).

A line of user U at time t is the run's whose lease of U holds t, give or take `eps` (the source is time-ordered only to about 20 ms; site_g's clock against the
run host's is not measured, and the lease margins on calibration-11's runs bound it). Not calibration's `matcher.attribute(margin_s=2.0)`: main's leases of one
user follow each other as little as 1.8 s apart, and 2 s on each side would make neighbours overlap. A line within `eps` of two leases is ambiguous and both
runs are left out, as calibration does. A line inside no lease is unattributed: counted per user, never given to the nearest run, since fault calibration,
the validation set and scripted work lease the same users and their leases are not in main's store."""
from __future__ import annotations

import bisect
import dataclasses
from collections import defaultdict
from typing import Iterable

from icsa.faults.records.base import AccessEvent

from .windows import Lease

EPS_S = 0.5


@dataclasses.dataclass
class Attribution:
    per_run: dict[tuple[str, str], list[AccessEvent]]
    ambiguous: dict[tuple[str, str], int]       # lines within eps of this lease and another of the same user
    unattributed: dict[str, int]                # by user: lines inside no lease
    eps: float


def attribute(events: Iterable[AccessEvent], leases: Iterable[Lease], eps: float = EPS_S) -> Attribution:
    by_user: dict[str, list[Lease]] = defaultdict(list)
    for ls in leases:
        by_user[ls.user].append(ls)
    starts, maxend = {}, {}
    for u, ls in by_user.items():
        ls.sort(key=lambda x: x.start)
        starts[u] = [x.start for x in ls]
        m, acc = float("-inf"), []
        for x in ls:
            m = max(m, x.end)
            acc.append(m)
        maxend[u] = acc                                  # the latest end among the leases up to each one: where a backward scan can stop
    per_run: dict[tuple[str, str], list[AccessEvent]] = defaultdict(list)
    ambiguous: dict[tuple[str, str], int] = defaultdict(int)
    unattributed: dict[str, int] = defaultdict(int)
    for ev in events:
        ls = by_user.get(ev.client or "")
        if not ls or ev.ts is None:
            unattributed[ev.client or ""] += 1
            continue
        i = bisect.bisect_right(starts[ev.client], ev.ts + eps)       # leases that start at or before t + eps
        hits, k = [], i - 1
        while k >= 0 and maxend[ev.client][k] >= ev.ts - eps:         # every candidate, not the last two (Astra, #12)
            if ls[k].end + eps >= ev.ts:
                hits.append(ls[k])
            k -= 1
        if len(hits) == 1:
            per_run[hits[0].ident].append(ev)
        elif hits:
            for x in hits:
                ambiguous[x.ident] += 1
        else:
            unattributed[ev.client] += 1
    return Attribution(dict(per_run), dict(ambiguous), dict(unattributed), eps)
