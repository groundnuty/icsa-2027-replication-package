"""The scheduling logic of the M+ driver (mplus_run.py), pure and stdlib-only: no clock, no file, no network, so test_mplus_gate.py tests it as it is.

A **piece** is one `mplus-measure --plan` call: layout L and a prefix n of L's seeded order. Its plan file lists `order[:n]` for L and [] for the other layout.
It has to be a prefix, because `mplus.measure` takes the cold/required alternation and the run tags from the instance's index j in the list it is given
(`cold-site_f-p{j}`, `mplus-required-p{j}`); `done_steps` makes it skip what the records already hold. One call per layout also keeps the registered shape: the layout
is provisioned once per call and read by every instance left. Nothing smaller than one layout call is safe: a transfer in flight is never cancelled
(`Campaign.require_ended`), and a call cannot be stopped from outside.

The projection is `mplus_project.project`'s formula (evict + cold wall, evict + required provisioning + M+ wall per instance not done; once per layout an evict, the layout
provisioning and one M+ layout wall per instance left), so the two agree on the same figures.
"""
from __future__ import annotations

import dataclasses
import datetime as dt

STEPS = ("cold-site_f", "mplus-required", "mplus-layout")
NEED = ("evict_s", "provision_required_s", "placed_bytes_required", "cold_site_f_wall_s", "mplus_required_wall_s")


def parse_utc(s: str) -> float:
    return dt.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc).timestamp()


def fmt_utc(t: float) -> str:
    return dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def expected_steps(layout: str, ids) -> set:
    return {(iid, layout, s) for iid in ids for s in STEPS}


def remaining(layout: str, ids, done) -> set:
    return expected_steps(layout, ids) - set(done)


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else None


def figures(st: dict, layout_prov_s, layout_run_walls, layout_bytes: float):
    """(figures, missing) of one layout from `mplus.step_times` and the measured layout provisioning / layout-scope M+ walls. A step with no clean sample for the
    five that every projection needs: figures None, and `missing` names them. The two layout figures fall back as `mplus_project` does: the provisioning scaled by bytes
    from the required scope's, the layout run taken from the required run; each carries whether it is measured."""
    missing = [k for k in NEED if not st.get(k)]
    if missing:
        return None, missing
    pl, ml = mean(layout_prov_s), mean(layout_run_walls)
    return {"evict_s": st["evict_s"], "cold_s": st["cold_site_f_wall_s"], "prov_req_s": st["provision_required_s"], "req_s": st["mplus_required_wall_s"],
            "prov_layout_s": pl if pl is not None else st["provision_required_s"] * layout_bytes / st["placed_bytes_required"],
            "layout_run_s": ml if ml is not None else st["mplus_required_wall_s"],
            "prov_layout_measured": pl is not None, "layout_run_measured": ml is not None}, []


def piece_seconds(fig: dict, layout: str, ids, done) -> float:
    e, c, p, m, pl, ml = fig["evict_s"], fig["cold_s"], fig["prov_req_s"], fig["req_s"], fig["prov_layout_s"], fig["layout_run_s"]
    s = 0.0
    for iid in ids:
        if (iid, layout, "cold-site_f") not in done:
            s += e + c
        if (iid, layout, "mplus-required") not in done:
            s += e + p + m
    left = [iid for iid in ids if (iid, layout, "mplus-layout") not in done]
    if left:
        s += e + pl + len(left) * ml
    return s


@dataclasses.dataclass
class Decision:
    run: bool
    n: int                      # prefix to run (0: none)
    reason: str
    est_s: float | None = None
    projected_end_utc: str | None = None
    rule: str = ""              # which test decided


def choose_prefix(layout: str, order, target_n: int, done, fig: dict | None, now: float, not_after: float, overhead_s: float, margin_s: float) -> Decision:
    """The largest prefix n <= target_n of `order` whose remaining work is projected to END by `not_after` - margin. Never a start at or after `not_after`.
    No figures (the barrier has not made them): the clock rule alone, the whole target. A prefix with nothing left stops the search: nothing further fits."""
    order = list(order)
    target_n = min(target_n, len(order))
    if not remaining(layout, order[:target_n], done):
        return Decision(False, target_n, "complete: every step of this prefix is already in the records", rule="done")
    if now >= not_after:
        return Decision(False, 0, f"the window closed at {fmt_utc(not_after)}", rule="clock")
    if fig is None:
        return Decision(True, target_n, "no step figures for this layout: the clock rule alone", rule="clock-only")
    for n in range(target_n, 0, -1):
        if not remaining(layout, order[:n], done):
            return Decision(False, n, f"nothing beyond the first {n} instance(s) is projected to end by {fmt_utc(not_after - margin_s)}", rule="projection")
        est = piece_seconds(fig, layout, order[:n], done)
        end = now + overhead_s + est
        if end + margin_s <= not_after:
            return Decision(True, n, f"first {n} of {len(order)}: projected end {fmt_utc(end)} (+ margin {margin_s:.0f} s) within {fmt_utc(not_after)}",
                            est_s=est, projected_end_utc=fmt_utc(end), rule="projection")
    return Decision(False, 0, "no prefix is projected to end in time", rule="projection")


def judge_dispatcher(alive: bool, running: int | None, quiet: dict | None, release_file: bool) -> tuple[str, str]:
    """Is main drained? PASS: no dispatcher process, or one paused by its quiet window (opened in its store, not released, no release file) with nothing in flight.
    A zero count of running attempts alone is not a drain: between two dispatches it reads the same, so an alive dispatcher without an open window is UNKNOWN.
    `quiet` is the `quiet_window` meta as a dict ({} when the key is absent), None when the store could not be read; `running` likewise."""
    if not alive:
        return "PASS", "no `icsa.campaign run` process"
    if running is None or quiet is None:
        return "UNKNOWN", "dispatcher alive and its store could not be read"
    if running > 0:
        return "FAIL", f"dispatcher alive, {running} attempt(s) running"
    if release_file:
        return "FAIL", "dispatcher alive and a quiet-window release file exists: dispatch may resume"
    if quiet.get("released_by"):
        return "FAIL", "dispatcher alive and its quiet window was released: dispatch resumed"
    if quiet.get("opened_utc"):
        return "PASS", f"dispatcher alive but paused by its quiet window (opened {quiet['opened_utc']}), 0 attempts running"
    return "UNKNOWN", "dispatcher alive, 0 attempts running, but no open quiet window in its store: a zero between two dispatches reads the same"


def rounds(mode: str, n_all: int = 5, n_reduced: int = 3):
    """The resume's pieces in order. literal: S1 whole, then S2 whole (the registered order of `measure`, layout by layout). balanced: 30(h)'s reduction first
    (3 of 5 per layout), then the rest, so a closed window leaves both layouts alike."""
    if mode == "literal":
        return [("S1", n_all), ("S2", n_all)]
    if mode == "balanced":
        return [("S1", n_reduced), ("S2", n_reduced), ("S1", n_all), ("S2", n_all)]
    raise ValueError(mode)
