"""Scoring parameters owned by the science agent (protocol config).

The "correct" threshold is the value in protocol/parameters.md: IoU of the
agent's and the reference's cell-day masks >= 0.9 on instances with reference
events (no cell-day = 1 on event-free instances). If it changes, load the
frozen value with `ScoringConfig.from_json` rather than editing the default.
"""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path


@dataclasses.dataclass(frozen=True)
class ScoringConfig:
    correct_iou_threshold: float = 0.9

    @classmethod
    def from_json(cls, path: str | Path) -> ScoringConfig:
        return cls(**json.loads(Path(path).read_text()))
