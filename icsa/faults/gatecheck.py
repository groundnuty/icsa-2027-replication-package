"""Amendment 17(c), check (i): on a fault-calibration run of T or D, which passes both the gate and Traefik, the H3 detector runs on both logs, and the gate log stands
in for Traefik's only if the flags are equal on every such run. `compare` is that, for one run; `calibrate.score` calls it on each T and D run and the score
command writes all of them, with `verdict` over the lot."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

from .detector import DetectorSpec, detect
from .records.base import AccessEvent, Kind, Record
from .records.gate import parse_gate
from .units import Manifest, Required


def _cut_downloads(gate_events: Sequence[AccessEvent]) -> list[dict]:
    """D's downloads the agent cut: Traefik shows the whole file, the gate what reached the agent."""
    out = []
    for e in gate_events:
        if e.kind is Kind.READ and e.range_header is None:
            d = json.loads(e.raw)
            if d.get("client_aborted") and d.get("upstream_bytes") is not None and e.content_size is not None and e.content_size < d["upstream_bytes"]:
                out.append({"target": e.target, "upstream_bytes": d["upstream_bytes"], "body_bytes": e.content_size})
    return out


def compare(run_key: str, gate_text: str | None, traefik_events: Sequence[AccessEvent], required: Required, manifest: Manifest) -> dict:
    """One run. `equal` is None when the gate log is missing or unreadable: not known is not agreement."""
    row: dict = {"run_key": run_key, "traefik_lines": len(traefik_events)}
    if gate_text is None:
        return {**row, "equal": None, "why": "no gate log"}
    try:
        parsed = parse_gate(gate_text)
    except ValueError as e:
        return {**row, "equal": None, "why": f"the gate log could not be read: {e}"[:300]}
    spec = DetectorSpec(Record.TRAEFIK)
    g, t = detect(parsed.events, required, manifest, spec), detect(list(traefik_events), required, manifest, spec)
    return {**row, "gate_lines": parsed.n_lines, "equal": g.missing == t.missing, "flags_gate": sorted(g.missing), "flags_traefik": sorted(t.missing),
            "only_gate": sorted(g.missing - t.missing), "only_traefik": sorted(t.missing - g.missing),
            "unresolved": {"gate": g.n_unresolved, "traefik": t.n_unresolved}, "used": {"gate": g.n_used, "traefik": t.n_used},
            "cut_downloads": _cut_downloads(parsed.events), "fingerprint": g.fingerprint}


def verdict(rows: Sequence[dict]) -> dict:
    """Check (i) over the calibration's T and D runs: it passes only when every run was compared and every one agreed."""
    unknown = [r["run_key"] for r in rows if r["equal"] is None]
    differ = [r["run_key"] for r in rows if r["equal"] is False]
    return {"runs": len(rows), "equal": sum(r["equal"] is True for r in rows), "differ": differ, "not_compared": unknown,
            "passes": bool(rows) and not unknown and not differ}


def gate_text_of(run_dir: Path) -> str | None:
    p = run_dir / "gate_requests.jsonl"
    return p.read_text() if p.exists() else None
