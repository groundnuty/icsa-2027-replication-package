"""Run-to-record matching, per record type.

What each record can attribute (from #10): the audit log has the user id and a timestamp, nothing
else (no session, token, client or IP); Traefik has ClientHost (the agent container's address) and
a timestamp; the oneclient perf CSV belongs to one sidecar by construction. So:

- An event is assigned to a run if its time lies in the run's window widened by `margin_s` (log
  flush lag, clock skew) AND, when the run names a principal, the event's client matches it.
- An event that fits two runs is AMBIGUOUS: it is assigned to neither, and both runs are flagged.
  Calibration should run serially with spacing > 2 * margin, or give each run its own principal.
- A run whose window was widened over another's, with ambiguous events in it, is not scored: its
  `excluded_reason` says so. Never guess.
- Perf CSVs are located by the run's sidecar identity (a directory named for it), never by
  scanning for the newest file.
"""
from __future__ import annotations

import dataclasses
import re
from pathlib import Path
from typing import Sequence

from .records.base import AccessEvent


@dataclasses.dataclass(frozen=True)
class RunWindow:
    run_key: str
    start: float                   # epoch s, UTC
    end: float
    principal: str | None = None   # audit: user id; traefik: ClientHost; perf: sidecar id


@dataclasses.dataclass(frozen=True)
class KnowledgePlane:
    """Identity of the knowledge plane's own requests (#6): they reach the same provider and ingress
    as the runs, so they are excluded from every record BY CONSTRUCTION, never counted as a run's
    reads and never as unattributable. Audit log: by Onedata user (the plane's own read-only
    principal). Traefik: by User-Agent prefix (`icsa-knowledge-plane/<pin>`). Configured in the
    slot-map file under "knowledge_plane": {"users": [...], "user_agent": "icsa-knowledge-plane/"}."""
    users: frozenset[str] = frozenset()
    user_agent: str = "icsa-knowledge-plane/"

    def __post_init__(self) -> None:
        if not self.user_agent:
            raise ValueError("an empty user-agent prefix would match every request")

    def matches(self, ev: AccessEvent) -> bool:
        return (ev.client is not None and ev.client in self.users) or \
               (ev.user_agent is not None and ev.user_agent.startswith(self.user_agent))


def split_knowledge_plane(events: Sequence[AccessEvent], kp: KnowledgePlane
                          ) -> tuple[list[AccessEvent], list[AccessEvent]]:
    """(run-relevant events, knowledge-plane events). `kp` is required at every entry point: a caller
    without a configured plane passes KnowledgePlane(), which still filters the default User-Agent prefix."""
    rest, mine = [], []
    for e in events:
        (mine if kp.matches(e) else rest).append(e)
    return rest, mine


@dataclasses.dataclass
class Attribution:
    run_key: str
    events: list[AccessEvent]
    n_kp_excluded: int = 0       # knowledge-plane lines that fall in this run's window: reported, not attributed
    n_ambiguous: int = 0
    n_untimed_skipped: int = 0
    overlaps: list[str] = dataclasses.field(default_factory=list)   # runs whose widened window overlaps this one's

    @property
    def excluded_reason(self) -> str | None:
        if self.overlaps:
            return f"run window overlaps {sorted(self.overlaps)} (same principal): attribution is ambiguous"
        if self.n_untimed_skipped:
            return f"{self.n_untimed_skipped} event(s) of this run's principal have no usable time: they may be its reads"
        return f"{self.n_ambiguous} ambiguous event(s) in the run window" if self.n_ambiguous else None


def attribute(events: Sequence[AccessEvent], windows: Sequence[RunWindow],
              margin_s: float = 2.0, *, kp: KnowledgePlane) -> dict[str, Attribution]:
    keys = [w.run_key for w in windows]
    if len(set(keys)) != len(keys):
        raise ValueError("duplicate run keys")
    out = {w.run_key: Attribution(w.run_key, []) for w in windows}
    # Windows that could share events are ambiguous whether or not an event happens to land in the
    # overlap: an empty record is evidence of "not read" only if no other run could have produced it.
    for i, a in enumerate(windows):
        for b in windows[i + 1:]:
            same = a.principal is None or b.principal is None or a.principal == b.principal
            if same and a.start - margin_s <= b.end + margin_s and b.start - margin_s <= a.end + margin_s:
                out[a.run_key].overlaps.append(b.run_key)
                out[b.run_key].overlaps.append(a.run_key)
    events, kp_events = split_knowledge_plane(events, kp)
    for ev in kp_events:                       # counted per window it falls in (any principal); never attributed
        if ev.ts is not None:
            for w in windows:
                if w.start - margin_s <= ev.ts <= w.end + margin_s:
                    out[w.run_key].n_kp_excluded += 1
    for ev in events:
        if ev.ts is None:
            for w in windows:              # cannot be placed in time: counted in every run it may belong to, assigned to none
                if w.principal is None or ev.client == w.principal:
                    out[w.run_key].n_untimed_skipped += 1
            continue
        hits = [w for w in windows
                if w.start - margin_s <= ev.ts <= w.end + margin_s
                and (w.principal is None or ev.client == w.principal)]   # unidentified events fit no principal-bound run
        if len(hits) == 1:
            out[hits[0].run_key].events.append(ev)
        elif len(hits) > 1:
            for w in hits:
                out[w.run_key].n_ambiguous += 1
    return out


_PERF_NAME = re.compile(r"^read_write_perf-(\d+)\.csv$")


def locate_perf_files(base: Path, sidecar_id: str) -> list[tuple[int, Path]]:
    """[(start epoch ms, path)] of this sidecar's CSVs, oldest first. Fails loudly if there are none.

    The directory is named for the sidecar. A path with separators in the id is refused, so one run
    can never be pointed at a peer's directory.
    """
    if not sidecar_id or "/" in sidecar_id or sidecar_id in (".", ".."):
        raise ValueError(f"bad sidecar id {sidecar_id!r}")
    d = base / sidecar_id
    found = sorted((int(m.group(1)), p) for p in d.glob("read_write_perf-*.csv")
                   if (m := _PERF_NAME.match(p.name)))
    if not found:
        raise FileNotFoundError(f"no read_write_perf-*.csv for sidecar {sidecar_id} under {d}")
    return found


# ---- attribution under concurrency, per record (see ATTRIBUTION.md) -------------------------
import json  # noqa: E402
from collections import defaultdict  # noqa: E402

from .records.base import Record  # noqa: E402


@dataclasses.dataclass(frozen=True)
class RunInterval:
    """What the scheduler records for each run: when it ran, in which concurrency slot, which option."""
    run_key: str
    option: str
    slot: str
    start: float          # epoch s, UTC
    end: float


@dataclasses.dataclass(frozen=True)
class Slot:
    user: str       # Onedata user id of this concurrency slot
    option: str     # the one option this slot serves (T, D or M)


KP_KEY = "knowledge_plane"


def load_slot_map(path: Path) -> dict[str, Slot]:
    """{slot: {"user": user_id, "option": option}}. One user per slot; each slot serves one option, so
    the user also tells the option (the audit line has no other discriminator)."""
    raw = json.loads(Path(path).read_text())
    if not isinstance(raw, dict) or not raw:
        raise ValueError("slot map must be a non-empty {slot: {user, option}} object")
    m = {}
    for k, v in raw.items():
        if k == KP_KEY:
            continue
        if not (isinstance(v, dict) and isinstance(v.get("user"), str) and v["user"]
                and isinstance(v.get("option"), str) and v["option"]):
            raise ValueError(f"slot {k!r}: needs non-empty string 'user' and 'option'")
        m[k] = Slot(v["user"], v["option"])
    if len({s.user for s in m.values()}) != len(m):
        raise ValueError("two slots share one Onedata user: runs in them cannot be told apart")
    kp = load_knowledge_plane(path)
    if kp and kp.users & {s.user for s in m.values()}:
        raise ValueError("the knowledge plane shares an Onedata user with a run slot")
    return m


def load_knowledge_plane(path: Path) -> KnowledgePlane | None:
    """The "knowledge_plane" entry of the slot-map file, or None if absent."""
    e = json.loads(Path(path).read_text()).get(KP_KEY)
    if e is None:
        return None
    users = e.get("users", []) if isinstance(e, dict) else None
    if not isinstance(users, list) or not all(isinstance(u, str) and u for u in users):
        raise ValueError("knowledge_plane.users must be a list of non-empty strings")
    ua = e.get("user_agent", "icsa-knowledge-plane/")
    if not isinstance(ua, str):
        raise ValueError("knowledge_plane.user_agent must be a string")
    return KnowledgePlane(frozenset(users), ua)


def option_of_user(slot_map: dict[str, Slot]):
    """A trusted option discriminator for attribute_audit_fallback(scope='option'): event user -> option."""
    by_user = {s.user: s.option for s in slot_map.values()}
    return lambda e: by_user.get(e.client)


def attribute_audit_by_slot(events: Sequence[AccessEvent], intervals: Sequence[RunInterval],
                            slot_map: dict[str, Slot], margin_s: float = 2.0,
                            *, kp: KnowledgePlane) -> dict[str, Attribution]:
    """Audit log, per-slot users: join on (user, time interval). A run whose slot has no user, or whose
    option is not the slot's option, fails loudly (the slot's user would then not identify the option)."""
    missing = sorted({i.slot for i in intervals} - set(slot_map))
    if missing:
        raise KeyError(f"slots without a user in the slot map: {missing}")
    wrong = [(i.run_key, i.option, slot_map[i.slot].option) for i in intervals if i.option != slot_map[i.slot].option]
    if wrong:
        raise ValueError(f"runs in a slot of another option (run, run option, slot option): {wrong}")
    wins = [RunWindow(i.run_key, i.start, i.end, slot_map[i.slot].user) for i in intervals]
    # an event with an unknown user fits no window (principal-bound), so a foreign user cannot leak in
    return attribute(events, wins, margin_s, kp=kp)


@dataclasses.dataclass
class FallbackReport:
    n_runs: int
    n_attributable: int
    by_option: dict[str, tuple[int, int]]       # option -> (attributable, total)
    unattributable: list[str]
    kp_by_run: dict[str, int] = dataclasses.field(default_factory=dict)   # knowledge-plane lines per run window, ALL runs

    @property
    def share(self) -> float:
        return self.n_attributable / self.n_runs if self.n_runs else float("nan")


def attribute_audit_fallback(events: Sequence[AccessEvent], intervals: Sequence[RunInterval],
                             margin_s: float = 2.0, scope: str = "all", option_of_event=None,
                             *, kp: KnowledgePlane, allow_unattributed: bool = False) -> tuple[dict[str, Attribution], FallbackReport]:
    """Audit log without per-slot users: only runs with no overlapping run in `scope` are matched.

    TIME-ONLY attribution. Calibration and the analysis attribute by slot user (`attribute_audit_by_slot`), the
    `X-ICSA-Run` header (`attribute_traefik_by_header`) and the run's own sidecar (`perf_events`) only, never by time
    (science, #11, 21:40Z). So this refuses to run unless the caller passes `allow_unattributed=True` explicitly; a test
    checks that no module under `icsa/` passes it.

    scope="all" (default, sound): no other run may overlap (widened by the margin).
    scope="option": only runs of the same option must not overlap. That is sound only if the
    audit lines of different options can be told apart, so the caller must pass `option_of_event`
    (event -> option, from a trusted discriminator such as a per-option user or space); events are
    partitioned by it before matching. Without it, scope="option" is refused.
    The report says how many runs the restriction covers.
    """
    if allow_unattributed is not True:
        raise ValueError("attribute_audit_fallback attributes by time only, which calibration and the analysis never do: "
                         "use attribute_audit_by_slot / attribute_traefik_by_header / perf_events, or pass "
                         "allow_unattributed=True explicitly")
    if scope not in ("option", "all"):
        raise ValueError(scope)
    if scope == "option" and option_of_event is None:
        raise ValueError("scope='option' needs option_of_event: without a trusted per-option discriminator use scope='all'")
    keys = [i.run_key for i in intervals]
    if len(set(keys)) != len(keys):
        raise ValueError("duplicate run keys")
    ok = []
    for a in intervals:
        clash = any(b is not a and (scope == "all" or b.option == a.option)
                    and a.start - margin_s <= b.end + margin_s and b.start - margin_s <= a.end + margin_s
                    for b in intervals)
        if not clash:
            ok.append(a)
    events, mine = split_knowledge_plane(events, kp)       # before any option partition: they are nobody's
    kp_by_run = {i.run_key: sum(1 for e in mine if e.ts is not None and i.start - margin_s <= e.ts <= i.end + margin_s)
                 for i in intervals}                       # counted for every run, attributable or not
    if scope == "all":
        att = attribute(events, [RunWindow(i.run_key, i.start, i.end) for i in ok], margin_s, kp=kp)
    else:
        att = {}
        for opt in sorted({i.option for i in ok}):
            att.update(attribute([e for e in events if option_of_event(e) == opt],
                                 [RunWindow(i.run_key, i.start, i.end) for i in ok if i.option == opt], margin_s, kp=kp))
    for k, a in att.items():
        a.n_kp_excluded = kp_by_run[k]
    by: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for i in intervals:
        by[i.option][1] += 1
    for i in ok:
        by[i.option][0] += 1
    rep = FallbackReport(len(intervals), len(ok), {k: (v[0], v[1]) for k, v in sorted(by.items())},
                         sorted(set(keys) - {i.run_key for i in ok}), kp_by_run)
    return att, rep


@dataclasses.dataclass
class RunKeyAttribution:
    by_run: dict[str, list[AccessEvent]]
    n_unattributable: int      # lines without the header
    n_unknown_key: int         # lines whose key is not a known run
    n_kp_excluded: int = 0     # knowledge-plane lines (by User-Agent): in neither count above
    kp_by_run: dict[str, int] = dataclasses.field(default_factory=dict)   # per run window, if windows were given


def attribute_traefik_by_header(events: Sequence[AccessEvent], windows: Sequence[RunWindow],
                                margin_s: float = 2.0, *, kp: KnowledgePlane) -> RunKeyAttribution:
    """Traefik: by the per-run header only. Client IP and time are NOT used (shared NAT, concurrent).
    Knowledge-plane lines (User-Agent) are excluded first and counted per run window (`windows` are required for it)."""
    run_keys = [w.run_key for w in windows]
    if len(set(run_keys)) != len(run_keys):
        raise ValueError("duplicate run keys")
    known = set(run_keys)
    out: dict[str, list[AccessEvent]] = {k: [] for k in run_keys}
    none = unk = 0
    events, mine = split_knowledge_plane(events, kp)
    by_run = {w.run_key: sum(1 for e in mine if e.ts is not None and w.start - margin_s <= e.ts <= w.end + margin_s)
              for w in windows}
    for e in events:
        if e.run_key is None:
            none += 1
        elif e.run_key not in known:
            unk += 1
        else:
            out[e.run_key].append(e)
    return RunKeyAttribution(out, none, unk, len(mine), by_run)


def perf_events(base: Path, sidecar_id: str, tz: str = "UTC", n_bad: list | None = None) -> list[AccessEvent]:
    """Perf log: attribution by construction (one sidecar per run). All of that sidecar's CSVs, in order. `n_bad`, if given,
    gets each file's count of rows that did not parse."""
    from .records.perf import parse_perf
    ev: list[AccessEvent] = []
    for start_ms, p in locate_perf_files(base, sidecar_id):
        r = parse_perf(p.read_text(), start_ms, sidecar_id, tz=tz)
        ev += r.events
        if n_bad is not None:
            n_bad.append(r.n_bad)
    return ev
