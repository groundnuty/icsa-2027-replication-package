import os, re
base = "/data/icsa2027_data_20261101T090944Z/s1z"
files = sorted(os.listdir(base))
dates = [f[4:12] for f in files if f.startswith("sst_") and f.endswith(".nc")]
print("n files:", len(files), "n sst:", len(dates))
print("min:", dates[0], "max:", dates[-1])
# check continuity
import datetime as dt
d0 = dt.date(int(dates[0][:4]), int(dates[0][4:6]), int(dates[0][6:8]))
d1 = dt.date(int(dates[-1][:4]), int(dates[-1][4:6]), int(dates[-1][6:8]))
ndays = (d1-d0).days + 1
print("span days:", ndays, "missing:", ndays - len(dates))
if ndays - len(dates) <= 20:
    have = set(dates)
    missing = [ (d0+dt.timedelta(i)).strftime("%Y%m%d") for i in range(ndays) if (d0+dt.timedelta(i)).strftime("%Y%m%d") not in have ]
    print("missing:", missing)
# check specific files we need
for d in ["19911227","20030105","20080601","20080831"]:
    print(d, f"sst_{d}.nc" in files)
