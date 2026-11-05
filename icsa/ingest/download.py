"""Resumable year-by-year Copernicus Marine download into ICSA_DATA/raw.

Run (unsandboxed, writes under /mnt/volume2):
    uv run python -m icsa.ingest.download [--first 1982] [--last 2023]

One `copernicusmarine subset` per year, as Bashiri et al.'s Step_0 script does,
but with the catalogue's current dataset id and max lon 30 (the 1051-column grid).
A year is complete when its file opens, has analysed_sst and the expected days.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys

import netCDF4

from icsa.paths import RAW

DATASET_ID = "cmems_obs-sst_bal_phy-temp_my_l4_P1D-m"
VARIABLE = "analysed_sst"
BOX = dict(lon=(9.0, 30.0), lat=(53.5, 66.0))


def year_file(year: int):
    return RAW / f"SST_BAL_{year}.nc"


def command(year: int, out_name: str) -> list[str]:
    return [
        "copernicusmarine", "subset",
        "--dataset-id", DATASET_ID,
        "--variable", VARIABLE,
        "--start-datetime", f"{year}-01-01T00:00:00",
        "--end-datetime", f"{year}-12-31T00:00:00",
        "--minimum-longitude", str(BOX["lon"][0]), "--maximum-longitude", str(BOX["lon"][1]),
        "--minimum-latitude", str(BOX["lat"][0]), "--maximum-latitude", str(BOX["lat"][1]),
        "--output-directory", str(RAW), "--output-filename", out_name,
        "--overwrite", "--disable-progress-bar", "--log-level", "ERROR",
    ]


def is_complete(year: int) -> bool:
    p = year_file(year)
    if not p.exists():
        return False
    ndays = (dt.date(year, 12, 31) - dt.date(year, 1, 1)).days + 1
    try:
        with netCDF4.Dataset(p) as ds:
            v = ds.variables[VARIABLE]
            return v.shape == (ndays, 626, 1051)
    except Exception:
        return False


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--first", type=int, default=1982)
    ap.add_argument("--last", type=int, default=2023)
    a = ap.parse_args(argv)
    RAW.mkdir(parents=True, exist_ok=True)
    log = RAW / "download_log.jsonl"
    failed = []
    for y in range(a.first, a.last + 1):
        if is_complete(y):
            print(f"{y}: complete, skipped", flush=True)
            continue
        tmp = f"SST_BAL_{y}.partial.nc"
        cmd = command(y, tmp)
        r = subprocess.run(cmd, input="Y\n", text=True)
        part = RAW / tmp
        if r.returncode == 0 and part.exists():
            part.replace(year_file(y))
        if is_complete(y):
            rec = {"year": y, "date": dt.datetime.now(dt.timezone.utc).isoformat(), "cmd": cmd}
            with open(log, "a") as f:
                f.write(json.dumps(rec) + "\n")
            print(f"{y}: downloaded", flush=True)
        else:
            failed.append(y)
            print(f"{y}: FAILED (rc={r.returncode})", flush=True)
    if failed:
        print("incomplete years:", failed, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
