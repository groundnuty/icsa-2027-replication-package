"""Endpoint slots for the open-weight models (~/icsa-paths/endpoints.json).

A session picks one slot at start and keeps every turn on it (each stack caches the prefix).
New sessions go to the up slot with the fewest active sessions; ties break on slot name.
"""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path


@dataclasses.dataclass(frozen=True)
class Slot:
    slot: str
    model: str
    api_id: str
    base_url: str
    up: bool
    backend_ends_utc: str | None = None
    backend: str = "hpc"             # "hpc" | "site_b"


class Noauthor_6vailable(RuntimeError):
    pass


class SlotPool:
    def __init__(self, slots: list[Slot]):
        self._slots = slots
        self._active: dict[str, int] = {s.slot: 0 for s in slots}

    @classmethod
    def from_file(cls, path: str | Path) -> "SlotPool":
        rows = json.loads(Path(path).expanduser().read_text())
        return cls([Slot(r["slot"], r["model"], r["api_id"], r["base_url"], bool(r["up"]),
                         r.get("backend_ends_utc")) for r in rows])

    def acquire(self, model: str) -> Slot:
        cands = [s for s in self._slots if s.model == model and s.up]
        if not cands:
            raise Noauthor_6vailable(f"no up slot for model {model!r}")
        best = min(cands, key=lambda s: (self._active[s.slot], s.slot))
        self._active[best.slot] += 1
        return best

    def release(self, slot: Slot) -> None:
        self._active[slot.slot] -= 1

    def active(self, slot: Slot) -> int:
        return self._active[slot.slot]


def lookup_slot(path: str | Path, name: str) -> Slot:
    """The slot the campaign (#16) picked, by name, from the endpoints file. A down slot is allowed:
    the campaign owns slot choice, the harness just uses it (a dead one surfaces as InfraError)."""
    for s in SlotPool.from_file(path)._slots:
        if s.slot == name:
            return s
    raise KeyError(f"slot {name!r} not in {path}")


SITE_B_PREFIX = "site_b:"


def resolve_slot(cfg, name: str) -> Slot:
    """Slot by name for a run: `site_b:<model>` is the logical site_b slot of that model (config
    [site_b]); anything else is an HPC slot of the endpoints file."""
    if not name.startswith(SITE_B_PREFIX):
        return lookup_slot(cfg.client.endpoints_file, name)
    want = name[len(SITE_B_PREFIX):]
    for spec in cfg.models.values():
        if spec.kind == "openai_compat" and want.lower() in (
                spec.key.lower(), spec.reported_name.lower(), spec.api_id.lower(), spec.api_id.split("/")[-1].lower()):
            return Slot(name, spec.key, spec.api_id, cfg.site_b["base_url"], True, None, "site_b")
    raise KeyError(f"no open-weight model matches site_b slot {name!r}")


def paused_models(pool: SlotPool, cfg, models: list[str]) -> set[str]:
    """Config keys of the models with no up slot: paused (waiting for a stack), not an agent failure.
    Slots are matched through ModelSpec.endpoint_name, the same name `acquire` uses."""
    return {m for m in models
            if not any(s.model == cfg.model(m).endpoint_name and s.up for s in pool._slots)}
