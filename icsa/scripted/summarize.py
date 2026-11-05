"""Run records -> tables. `python -m icsa.scripted.summarize <results_dir>`; no plotting.

A results directory holds `runs/<key>/run.json`. A field absent from a record is None in the row, never 0."""
from __future__ import annotations

import csv
import json
import statistics
import sys
from pathlib import Path


def load_runs(results_dir) -> list[dict]:
    """Every runs/*/run.json, sorted by run_key. Invalid JSON raises: nothing is skipped silently."""
    out = []
    for p in sorted(Path(results_dir).glob("runs/*/run.json")):
        try:
            r = json.loads(p.read_text())
        except json.JSONDecodeError as e:
            raise ValueError(f"{p}: invalid JSON: {e}") from e
        if not isinstance(r, dict):
            raise ValueError(f"{p}: not a JSON object")
        out.append(r)
    return sorted(out, key=lambda r: str(r.get("run_key", "")))


def _g(d, *path):
    for k in path:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def _diff(a, b):
    return None if a is None or b is None else round(a - b, 6)


def run_row(r: dict) -> dict:
    st = _g(r, "script", "stamps_s")
    st = st if isinstance(st, dict) else {}
    by_tag = _g(r, "gate_requests", "by_tag")
    by_tag = by_tag if isinstance(by_tag, dict) else None
    ups = [_g(v, "upstream_bytes") for v in by_tag.values()] if by_tag is not None else []
    ups = [u for u in ups if u is not None]
    errors = r.get("errors")
    errors = errors if isinstance(errors, list) else []
    return {
        "run_key": r.get("run_key"), "tag": r.get("tag"), "attempt": r.get("attempt"),
        "instance_id": r.get("instance_id"), "option": r.get("option"), "layout": r.get("layout"),
        "level": _g(r, "extra", "level"), "rep": _g(r, "extra", "rep"),
        "ok": r.get("ok"), "n_errors": len(errors), "first_error": str(errors[0])[:200] if errors else "",
        "wall_s": r.get("wall_s"), "pipeline_s": _g(r, "script", "pipeline_s"),
        "first_compute_s": _g(r, "script", "first_compute_s"),
        "read_s": _diff(st.get("read_done"), st.get("listing_done")),
        "compute_s": _diff(st.get("compute_done"), st.get("read_done")),
        "listing_s": _diff(st.get("listing_done"), st.get("client_ready")),
        "listing_entries": _g(r, "script", "listing_entries"),
        "sandbox_start_s": r.get("sandbox_start_s"),
        "between_sites_rx": _g(r, "bytes", "between_sites_rx"),
        "agent_eth0_rx": _g(r, "bytes", "agent_eth0", "rx"),
        "gate_upstream_rx": _g(r, "bytes", "gate_upstream", "rx"),
        "sidecar_rx": _g(r, "bytes", "sidecar_bridge", "rx"),
        "client_requests": r.get("client_requests"),
        "content_requests": _g(by_tag, "content", "requests") if by_tag is not None else None,
        "gate_non_2xx": _g(r, "gate_requests", "non_2xx"),
        "upstream_errors": _g(r, "gate_requests", "upstream_errors"),
        "upstream_timeouts": _g(r, "gate_requests", "upstream_timeouts"),
        "gate_reconnects": _g(r, "gate_requests", "reconnects"),
        "attrs_timeouts": _g(by_tag, "attrs", "upstream_timeouts") if by_tag is not None else None,
        "content_timeouts": _g(by_tag, "content", "upstream_timeouts") if by_tag is not None else None,
        "variant": _g(r, "extra", "variant"),
        "traced": _g(r, "extra", "traced"),
        # None when any counter is unknown: a sum over the known ones would read as a clean zero
        "oom_kills": (sum(r["oom_kills"].values()) if r.get("oom_kills") and None not in r["oom_kills"].values() else None),
        # the gate's run flags (#7, fix/7-gate-keepalive); None where the sandbox predates them or there is no gate
        "agent_saw_gate_error": _g(r, "sandbox", "gate_transfers", "agent_saw_gate_error"),
        "agent_saw_upstream_error": _g(r, "sandbox", "gate_transfers", "agent_saw_upstream_error"),
        "upstream_bytes_whole_file": sum(ups) if by_tag is not None else None,
        "mask_equal": _g(r, "compare", "mask", "equal"),
        "events_equal": _g(r, "compare", "events_equal"),
        "sst_equal": _g(r, "compare", "sst_equal"),
        "compare_equal": _g(r, "compare", "equal"),
        "access_type": _g(r, "script", "access_type"),
        "mem_available_min_gib": r.get("mem_available_min_gib"),
        "load1_before": _g(r, "host_before", "load1"),
        "other_sandboxes_before": _g(r, "host_before", "other_sandboxes"),
        "oneclient_fslogic_reads": _g(r, "oneclient_perf", "by_operation", "FsLogic.read", "count"),
        "oneclient_prefetches": _g(r, "oneclient_perf", "by_operation", "ReadCache.prefetch", "count"),
    }


def write_csv(rows, path) -> None:
    rows = list(rows)
    cols: list[str] = []
    for r in rows:
        for k in r:
            if k not in cols:
                cols.append(k)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in rows:
            w.writerow(["" if r.get(c) is None else r.get(c) for c in cols])


def _med(xs):
    xs = [x for x in xs if x is not None]
    return statistics.median(xs) if xs else None


def cell_summary(rows) -> list[dict]:
    cells: dict[tuple, list[dict]] = {}
    for r in rows:
        lv = 1 if r.get("level") is None else r["level"]
        cells.setdefault((r.get("option"), r.get("layout"), lv), []).append(r)
    out = []
    for (opt, lay, lv), rs in sorted(cells.items(), key=lambda kv: tuple(str(x) for x in kv[0])):
        good = [r for r in rs if r.get("ok") is True]
        walls = [r["wall_s"] for r in good if r.get("wall_s") is not None]
        out.append({"option": opt, "layout": lay, "level": lv, "runs": len(rs), "ok": len(good),
                    "wall_s_median": statistics.median(walls) if walls else None,
                    "wall_s_min": min(walls) if walls else None, "wall_s_max": max(walls) if walls else None,
                    "between_sites_rx_median": _med(r.get("between_sites_rx") for r in good),
                    "client_requests_median": _med(r.get("client_requests") for r in good),
                    "first_compute_s_median": _med(r.get("first_compute_s") for r in good)})
    return out


def difference_report(rows) -> list[dict]:
    keys = ("run_key", "compare_equal", "mask_equal", "events_equal", "sst_equal", "first_error")
    return [{k: r.get(k) for k in keys} for r in rows if r.get("compare_equal") is not True or r.get("ok") is not True]


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: python -m icsa.scripted.summarize <results_dir>", file=sys.stderr)
        return 2
    d = Path(argv[0])
    rows = [run_row(r) for r in load_runs(d)]
    write_csv(rows, d / "runs.csv")
    cells = cell_summary(rows)
    write_csv(cells, d / "cells.csv")
    (d / "differences.json").write_text(json.dumps(difference_report(rows), indent=1))
    for c in cells:
        print(f"{c['option']} {c['layout']} level={c['level']}: runs={c['runs']} ok={c['ok']} "
              f"wall_s median={c['wall_s_median']} min={c['wall_s_min']} max={c['wall_s_max']} "
              f"between_sites_rx median={c['between_sites_rx_median']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
