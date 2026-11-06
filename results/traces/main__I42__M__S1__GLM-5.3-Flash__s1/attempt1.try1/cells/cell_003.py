import os, re
base = "/data/icsa2027_data_20261101T090944Z/s1z"
files = sorted(os.listdir(base))
print(len(files), files[0], files[-1])
dates = [f[4:12] for f in files if f.startswith("sst_") and f.endswith(".nc")]
dates = sorted(dates)
print("first,last:", dates[0], dates[-1])
# check continuity
from datetime import date, timedelta
missing = []
d = date(int(dates[0][:4]), int(dates[0][4:6]), int(dates[0][6:8]))
last = date(int(dates[-1][:4]), int(dates[-1][4:6]), int(dates[-1][6:8]))
have = set(dates)
while d <= last:
    s = d.strftime("%Y%m%d")
    if s not in have:
        missing.append(s)
    d += timedelta(days=1)
print("missing count:", len(missing), missing[:20])
# ranges of interest
need = [x for x in dates if "1991-12-27" <= f"{x[:4]}-{x[4:6]}-{x[6:]}" <= "2003-01-05"]
print("baseline-ish files:", len(need), need[0], need[-1])
t = [x for x in dates if "2012-06-01" <= f"{x[:4]}-{x[4:6]}-{x[6:]}" <= "2012-08-31"]
print("target files:", len(t), t[0], t[-1])
