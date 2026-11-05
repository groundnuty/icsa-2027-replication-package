"""Cost measures from the run record (#8)."""
from __future__ import annotations

import dataclasses

from ..records import RunRecord


@dataclasses.dataclass(frozen=True)
class Cost:
    input_tokens: int
    output_tokens: int
    wall_time_s: float
    bytes_between_sites: int | None
    bytes_into_context: int
    tokens_into_context: int | None
    # input_tokens is the whole prompt; for Claude it is uncached + cache-write + cache-read (None where unsplit)
    uncached_input_tokens: int | None = None
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0


COUNTED_TOKENS = ("provider tokenizer", "no tool outputs")


def _tokens_into_context(rec: RunRecord) -> int | None:
    """The tokenizer's count, or None if the record does not say it was counted. A run's turns hold 0 by default, so only
    the source can tell a count from the absence of one."""
    if rec.extras.get("tokens_into_context_source") not in COUNTED_TOKENS:
        return None
    counts = [t.tokens_into_context for t in rec.turns]
    return None if any(c is None for c in counts) else sum(counts)


def run_cost(rec: RunRecord) -> Cost:
    # Sandbox.bytes_moved, by way of the runner. None means "not known", never zero.
    b = rec.extras.get("bytes_between_sites")
    return Cost(
        input_tokens=sum(t.input_tokens for t in rec.turns),
        output_tokens=sum(t.output_tokens for t in rec.turns),
        wall_time_s=rec.wall_time_s,
        bytes_between_sites=int(b) if b is not None else None,
        bytes_into_context=sum(t.bytes_into_context for t in rec.turns),
        tokens_into_context=_tokens_into_context(rec),
        uncached_input_tokens=(None if all(t.uncached_input_tokens is None for t in rec.turns)
                               else sum(t.uncached_input_tokens or 0 for t in rec.turns)),
        cache_creation_input_tokens=sum(t.cache_creation_input_tokens for t in rec.turns),
        cache_read_input_tokens=sum(t.cache_read_input_tokens for t in rec.turns))
