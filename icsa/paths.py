"""Where data and run outputs live. Override the root with ICSA_DATA."""
from __future__ import annotations

import os
from pathlib import Path

DATA_ROOT = Path(os.environ.get("ICSA_DATA", "/mnt/volume2/icsa-2027"))
REF = DATA_ROOT / "ref"          # published reference data and code (Bashiri et al. 2025)
RAW = DATA_ROOT / "raw"          # the Copernicus download, as downloaded
S1_DIR = DATA_ROOT / "s1"        # 15,340 daily files, one flat directory
S2_FILE = DATA_ROOT / "s2" / "sst_s2.nc"
# Deflate-4 (lossless) rebuild, operator decision on #3 (02:21Z 1 Nov): the ingest tools default to these.
S1Z_DIR = DATA_ROOT / "s1z"
S2Z_FILE = DATA_ROOT / "s2z" / "sst_s2.nc"
RUNS = DATA_ROOT / "runs"        # one directory per run
