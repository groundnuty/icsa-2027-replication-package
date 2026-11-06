import fsspec
fs = fsspec.filesystem('onedata')
names = sorted(e.get('name') for e in fs.ls('icsa2027_data_20261101T090944Z/s1z', detail=True))
print("n files:", len(names))
print("first:", names[:3])
print("last:", names[-3:])
# check for any non .nc
import re
bad = [n for n in names if not n.endswith('.nc')]
print("bad names:", bad[:10])
# check for missing dates
dates = [n[4:12] for n in names if n.endswith('.nc')]
dates_sorted = sorted(dates)
print("date range:", dates_sorted[0], dates_sorted[-1])
# check continuity
import datetime as dt
d0 = dt.date(int(dates_sorted[0][:4]), int(dates_sorted[0][4:6]), int(dates_sorted[0][6:8]))
d1 = dt.date(int(dates_sorted[-1][:4]), int(dates_sorted[-1][4:6]), int(dates_sorted[-1][6:8]))
expected = (d1 - d0).days + 1
print("expected days:", expected, "actual:", len(set(dates)))
missing = []
cur = d0
have = set(dates)
while cur <= d1:
    if cur.strftime("%Y%m%d") not in have:
        missing.append(cur.isoformat())
    cur += dt.timedelta(days=1)
print("missing count:", len(missing), missing[:20])
