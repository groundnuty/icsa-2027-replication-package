import fsspec
fs = fsspec.filesystem('onedata')
entries = fs.ls('icsa2027_data_20261101T090944Z/s1z', detail=True)
names = sorted(e['name'] for e in entries)
print("count:", len(names))
print("first:", names[0], "last:", names[-1])
# check for unexpected names
import re
bad = [n for n in names if not re.fullmatch(r'sst_\d{8}\.nc', n)]
print("bad names:", bad[:20], len(bad))
dates = sorted(n[4:12] for n in names if re.fullmatch(r'sst_\d{8}\.nc', n))
print("date range:", dates[0], dates[-1])
# check duplicates / gaps near our needs
import datetime as dt
ds = [dt.datetime.strptime(d, "%Y%m%d").date() for d in dates]
# look for missing days in 1990-2004
d0 = dt.date(1990,1,1); d1 = dt.date(2004,12,31)
all_days = set()
cur = d0
while cur <= d1:
    all_days.add(cur)
    cur += dt.timedelta(days=1)
present = set(ds)
missing = sorted(all_days - present)
print("missing days in 1990-2004:", len(missing))
print(missing[:30])
