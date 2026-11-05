"""Run a ReadPlan against a byte reader. Option-agnostic: the plan is the same for T, D and M; only
the mechanism differs (T and M read byte ranges; D downloads whole files). No model is involved.

`ByteReader` is implemented per option by the live harness (T: fsspec REST client range reads;
D: whole-file download; M: reads on the oneclient mount) -- not here, because live runs wait for
the sandbox (#7) and the data (#3). `execute` returns the list of operations it issued, so tests
can check the script does exactly what the scenario says.
"""
from __future__ import annotations

from typing import Protocol

from icsa.records import Layout, Option

from .scenarios import Mode, ReadPlan
from .units import Manifest


class ByteReader(Protocol):
    def read_range(self, file_key: str, start: int, end: int) -> bytes: ...
    def download(self, file_key: str) -> bytes: ...


def execute(plan: ReadPlan, manifest: Manifest, option: Option, reader: ByteReader) -> list[tuple]:
    ops: list[tuple] = []
    downloaded: set[str] = set()
    headers_done: set[str] = set()
    for day in sorted(plan.touch):
        mode = plan.touch[day]
        key, a, b = manifest.units[day]
        if option is Option.D:
            if key not in downloaded:             # the option's mechanism: any touch downloads the file
                reader.download(key); ops.append(("download", key)); downloaded.add(key)
            continue
        if mode is Mode.HEADER:
            if key not in headers_done:
                end = manifest.data_start(key)    # strictly below the first data byte
                reader.read_range(key, 0, end); ops.append(("range", key, 0, end)); headers_done.add(key)
        else:
            lo, hi = (0, manifest.file(key).size) if manifest.layout is Layout.S1 else (a, b)
            reader.read_range(key, lo, hi); ops.append(("range", key, lo, hi))
    return ops
