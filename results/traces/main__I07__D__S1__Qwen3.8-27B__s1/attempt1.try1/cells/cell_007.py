import fsspec, os, re, time
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

needed = set()
from datetime import date, timedelta
# baseline extended range
d = date(1991,12,27)
end = date(2003,1,5)
while d <= end:
    needed.add(d); d += timedelta(days=1)
d = date(2021,6,1)
end2 = date(2021,8,31)
while d <= end2:
    needed.add(d); d += timedelta(days=1)
print("needed days:", len(needed))

def fname(dt): return f"sst_{dt.year:04d}{dt.month:02d}{dt.day:02d}.nc"

# glob per year to discover existing files
years = sorted({dt.year for dt in needed})
print("years:", years)
existing = set()
for y in years:
    pat = f"{base}/sst_{y:04d}*.nc"
    res = fs.glob(pat)
    print(y, len(res))
    for r in res:
        n = os.path.basename(r)
        m = re.match(r'sst_(\d{8})\.nc', n)
        if m:
            existing.add(m.group(1))

missing = []
for dt in sorted(needed):
    k = f"{dt.year:04d}{dt.month:02d}{dt.day:02d}"
    if k not in existing:
        missing.append(dt)
print("missing:", missing[:20], "count:", len(missing))
