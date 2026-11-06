import fsspec, re
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
entries = fs.ls(base, detail=False)
print("n entries:", len(entries))
names = [e.split('/')[-1] for e in entries]
# check all match pattern
pat = re.compile(r'^sst_(\d{8})\.nc$')
dates = []
bad = [n for n in names if not pat.match(n)]
print("bad:", bad[:10])
dates = [n[4:12] for n in names]
dates = sorted(d for d in dates if pat.match('sst_'+d+'.nc'))
print("min:", dates[0], "max:", dates[-1], "count:", len(dates))
# check duplicates / gaps
from datetime import date, timedelta
d0 = date(int(dates[0][:4]), int(dates[0][4:6]), int(dates[0][6:8]))
d1 = date(int(dates[-1][:4]), int(dates[-1][4:6]), int(dates[-1][6:8]))
expect = (d1-d0).days + 1
print("expected days:", expect, "have:", len(dates))
dset = set(dates)
missing = []
d = d0
while d <= d1:
    s = d.strftime('%Y%m%d')
    if s not in dset:
        missing.append(s)
    d += timedelta(days=1)
print("missing:", len(missing), missing[:20])
