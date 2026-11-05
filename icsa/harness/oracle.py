"""The oracle agent: a scripted agent that does the task correctly, run through the real loop,
tools and sandbox like any model.

It is a StubAdapter whose turns are python cells. Its analysis is `oracle_analysis.py`, a literal
implementation of the prompt's Method (not derived from #4). Each cell first runs the option's
access snippet, which defines `load_region(lat_min, lat_max, lon_min, lon_max, date_ranges) -> (sst, dates,
lat, lon)` by reading the data through that option's enforced path (T, T-unpaginated, D, M, M+ over
S1/S2). The snippets for the real paths belong to the sandbox lane (#7) and are supplied as
`access_snippets`; this module ships only `local_files_snippet`, a plain-filesystem reader for
tests on synthetic data (not an enforced path of any option).
"""
from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Callable

from icsa import grid
from icsa.records import Instance, Layout, Option

from .adapters import StubAdapter

AccessSnippets = Callable[[Option, Layout, dict], str]
ANALYSIS_SOURCE = Path(__file__).with_name("oracle_analysis.py").read_text().replace(
    "from __future__ import annotations\n", "")   # a __future__ import cannot follow the access snippet


def local_files_snippet(option: Option, layout: Layout, data_config: dict) -> str:
    """Plain-filesystem reader (STAND-IN data path, tests only). S1: sst_<day>.npy per day, each
    (lat, lon) of the stored crop at the grid origin; S2: one sst_s2.npy (days, lat, lon)."""
    root = data_config["local_root"]
    read = (f'np.stack([np.load(f"{root}/s1/sst_{{d:05d}}.npy") for d in range({grid.NDAYS})])'
            if layout is Layout.S1 else f'np.load(f"{root}/s2/sst_s2.npy")')
    return textwrap.dedent(f"""
        import numpy as np, datetime
        def load_region(lat_min, lat_max, lon_min, lon_max, date_ranges):
            a = {read}
            lat = np.array([53.5 + 0.02 * j for j in range(a.shape[1])]); lon = np.array([9.0 + 0.02 * i for i in range(a.shape[2])])
            jl = (lat >= lat_min) & (lat <= lat_max); il = (lon >= lon_min) & (lon <= lon_max)
            alld = [datetime.date(1982, 1, 1) + datetime.timedelta(days=i) for i in range(a.shape[0])]
            keep = [i for i, d in enumerate(alld) if any(s <= d <= e for s, e in date_ranges)]
            return a[keep][:, jl][:, :, il], [alld[i] for i in keep], lat[jl], lon[il]
    """)


def oracle_cells(instance: Instance, access: str) -> list[str]:
    region = {"lat_min": instance.lat_min, "lat_max": instance.lat_max,
              "lon_min": instance.lon_min, "lon_max": instance.lon_max}
    call = (f"\nimport datetime\nrun(load_region, {region!r}, datetime.date.fromisoformat({instance.target.start.isoformat()!r}),"
            f" datetime.date.fromisoformat({instance.target.end.isoformat()!r}))\n")
    return [access + "\nprint('access ok')\n", access + "\n" + ANALYSIS_SOURCE + call]


def oracle_adapter(instance: Instance, option: Option, layout: Layout, data_config: dict,
                   access_snippets: AccessSnippets = local_files_snippet, seed: int = 0) -> StubAdapter:
    access = access_snippets(option, layout, data_config)
    turns = [[("python", {"code": c})] for c in oracle_cells(instance, access)]
    turns.append("Both files are written.")
    return StubAdapter(turns, name="oracle", seed=seed)
