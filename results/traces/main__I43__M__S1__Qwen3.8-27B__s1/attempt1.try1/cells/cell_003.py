import os, re
base = "/data/icsa2027_data_20261101T090944Z/s1z"
files = os.listdir(base)
print(len(files))
dates = sorted(f[4:12] for f in files if re.fullmatch(r"sst_\d{8}\.nc", f))
print(dates[0], dates[-1])
years = sorted(set(d[:4] for d in dates))
print(years)
# check missing days per year
from datetime import date, timedelta
missing = {}
for d in dates:
    pass
have = set(dates)
all_dates = set()
cur = date(1991,1,1)
while cur.year < 2025:
    cur += timedelta(days=1)
d0 = date(1991,1,1)
d1 = date(2026,1,1)
cur = d0
while cur < d1:
    s = cur.strftime("%Y%m%d")
    if s not in have:
        missing.setdefault(cur.year, []).append(cur)
    cur += timedelta(days=1)
for y in years:
    miss = missing.get(y, [])
    print(y, "missing:", len(miss), [m.strftime("%m-%d") for m in miss[:10]])
