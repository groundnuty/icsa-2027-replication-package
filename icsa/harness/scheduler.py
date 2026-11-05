"""Run planning and scheduling.

Deliberately minimal: ordering, resumption and retries belong to the campaign (#16).
`run_all` executes the plan in the order given, with one worker pool per provider (cap from config);
the executor starts and stops its own fresh sandbox per run, and the provider concurrency at each
run's start is passed to it so it lands on the record.
"""
from __future__ import annotations

import asyncio
import dataclasses
from pathlib import Path
from typing import Awaitable, Callable, Iterable

from icsa.records import Instance, RunId

from .config import HarnessConfig


@dataclasses.dataclass
class Completed:
    run: RunId
    record: object | None
    paused: bool = False          # not run: its model has no up slot (waiting, not an agent failure)


async def run_all(plan: list[tuple[Instance, RunId]], cfg: HarnessConfig,
                  execute: Callable[[RunId, Instance, int], Awaitable[object]],
                  max_parallel: int | None = None, paused_models: frozenset[str] | set[str] = frozenset()
                  ) -> list[Completed]:
    """`execute(run, instance, concurrency_at_start)` runs one run (see runner.execute_run)."""
    in_flight: dict[str, int] = {p: 0 for p in cfg.provider_concurrency}
    gate = asyncio.Semaphore(max_parallel) if max_parallel else None
    out: list[Completed] = []
    queues: dict[str, asyncio.Queue] = {p: asyncio.Queue() for p in cfg.provider_concurrency}
    for inst, run in plan:
        if cfg.model(run.model).key in paused_models:           # a model with no up slot is paused, never run and never failed
            out.append(Completed(run, None, paused=True))
            continue
        # each provider's runs keep the shuffled order
        queues[cfg.concurrency_unit(cfg.model(run.model))].put_nowait((inst, run))

    async def one(provider: str, inst: Instance, run: RunId) -> None:
        async def counted() -> object:
            in_flight[provider] += 1                 # counted only while actually executing
            try:
                return await execute(run, inst, in_flight[provider])
            finally:
                in_flight[provider] -= 1
        if gate:
            async with gate:
                out.append(Completed(run, await counted()))
        else:
            out.append(Completed(run, await counted()))

    async def worker(provider: str) -> None:
        while True:
            try:
                inst, run = queues[provider].get_nowait()
            except asyncio.QueueEmpty:
                return
            await one(provider, inst, run)

    # one pool per provider, sized by its cap: a saturated provider never holds back another's runs
    await asyncio.gather(*[worker(p) for p, n in cfg.provider_concurrency.items() for _ in range(n)])
    return out
