import os
base = "/data/icsa2027_data_20261101T090944Z/s1z"
files = sorted(f for f in os.listdir(base) if f.startswith("sst_") and f.endswith(".nc"))
print("n files:", len(files))
print("first:", files[0], "last:", files[-1])
# check gaps
import datetime
dates = [datetime.datetime.strptime(f[4:12], "%Y%m%d").date() for f in files]
gaps = []
for a, b in zip(dates, dates[1:]):
    if (b - a).days != 1:
        gaps.append((a, b))
print("gaps:", gaps[:20])
print("min date:", dates.min(), "max date:", dates.max())
# any other files?
others = [f for f in os.listdir(base) if not (f.startswith("sst_") and f.endswith(".nc"))]
print("others:", others[:10])
