"""The expected-extent metadata stored on each layout's dataset root (#6).

Built from #3's extent JSON (`data/extent_s1.json`, `extent_s2.json`) by a whitelist: nothing is recomputed and
nothing outside the whitelist (source dataset, upload and checksum details, out-of-range statistics) is copied.
It states what the dataset is, never which files exist or how they are named. The two layouts differ only in
`layout` and `files`.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from icsa import grid
from icsa.records import Layout

KEEP = ("variable", "long_name", "units", "dtype", "missing_value", "time", "grid", "layout")
S1_DIRNAME, S2_DIRNAME = "s1z", "s2z"     # #3's layout under the study space; roots = /<space>/s1z and /<space>/s2z/sst_s2.nc
FILE_WORDS = re.compile(r"\.nc\b|\.h5\b|\bsst_|\d{8}|[A-Za-z0-9_]+\.(?:nc|h5|hdf5)\b|\bs[12]z\b", re.I)


def build(extent: dict, layout: Layout) -> dict:
    meta = {k: json.loads(json.dumps(extent[k])) for k in KEEP}
    if layout is Layout.S1:
        n = extent["number_of_files"]
        meta["files"] = {"count": n, "description": f"{n} files, one per day, in one flat directory"}
    else:
        n = extent.get("number_of_files", 1)
        if n != 1:
            raise ValueError(f"S2 extent says {n} files; the layout is a single file")
        meta["files"] = {"count": 1, "description": "a single file holding all days"}
    check(meta, layout)
    return meta


def check(meta: dict, layout: Layout) -> None:
    """Refuse a metadata document that is not what the study promises. Raises ValueError."""
    t, g = meta["time"], meta["grid"]
    if (t["start"], t["end"], t["step"]) != ("1982-01-01", "2023-12-31", "1 day") or t["count"] != grid.NDAYS:
        raise ValueError(f"time range differs from the shared grid: {t}")
    if list(g["shape_lat_lon"]) != [grid.NLAT, grid.NLON] or g["resolution_deg"] != 0.02:
        raise ValueError(f"grid differs from the shared grid: {g}")
    if meta["variable"] != "analysed_sst" or meta["units"] != "kelvin" or "NaN" not in str(meta["missing_value"]):
        raise ValueError("variable, units or land-cell rule differ from the protocol")
    if set(meta) != set(KEEP) | {"files"}:
        raise ValueError(f"unexpected keys: {sorted(set(meta) ^ (set(KEEP) | {'files'}))}")
    text = json.dumps(meta)
    m = FILE_WORDS.search(text)
    if m:
        raise ValueError(f"metadata names a file or directory ({m.group(0)!r}); it must not")
    want = 15340 if layout is Layout.S1 else 1
    if meta["files"]["count"] != want:
        raise ValueError(f"file count {meta['files']['count']} for {layout}")


def frozen_path(layout: Layout) -> Path:
    from .pin import KNOWLEDGE_DIR
    return KNOWLEDGE_DIR / f"extent_{layout.value.lower()}.json"


def _main() -> None:
    import sys
    for layout, src in ((Layout.S1, sys.argv[1]), (Layout.S2, sys.argv[2])):
        meta = build(json.loads(Path(src).read_text()), layout)
        frozen_path(layout).write_text(json.dumps(meta, indent=1, sort_keys=True) + "\n")
        print("wrote", frozen_path(layout))


if __name__ == "__main__":
    _main()
