"""Finished-run validity: a thin call into the ONE frozen parser, icsa.scoring.report (#13).

A run is *finished* iff it ended with a final assistant message containing no tool call, before any
cap or error (the loop's `ending == "final_message"`), AND the frozen parser accepts both output
files. The harness carries no parsing rules of its own.
"""
from __future__ import annotations

from pathlib import Path

from icsa.extent import CellBox
from icsa.ncio import NETCDF_LOCK
from icsa.records import Instance
from icsa.scoring.reference import target_days_of
from icsa.scoring.report import ParsedOutput, parse_run_output


# netCDF4/HDF5 is not safe for concurrent use from several threads of one process (a six-thread read crashed the
# interpreter), and runs execute on worker threads: every parse of a run's files goes through this lock.


def parse_outputs(out_dir: str | Path, instance: Instance) -> ParsedOutput:
    with NETCDF_LOCK:
        return _parse_outputs(out_dir, instance)


def _parse_outputs(out_dir: str | Path, instance: Instance) -> ParsedOutput:
    box = CellBox(instance.lat0, instance.lat1, instance.lon0, instance.lon1)
    return parse_run_output(Path(out_dir), box, target_days_of(instance))


def validate_outputs(out_dir: str | Path, instance: Instance) -> tuple[bool, str]:
    p = parse_outputs(out_dir, instance)
    if p.valid:
        return True, "ok"
    return False, "; ".join(f"{k}: {v}" for k, v in sorted(p.reasons.items()))
