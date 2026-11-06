
import fsspec, datetime
fs = fsspec.filesystem('onedata')
base = '/icsa2027_data_20261101T090944Z/s1z'

def ymd(s): return s[4:6], s[6:8]

# Build list of required dates
req = set()
d = datetime.date(1991,12,27)
end = datetime.date(2003,1,5)
while d <= end:
    req.add(d); d += datetime.timedelta(days=1)
d = datetime.date(2014,6,1)
while d <= datetime.date(2014,8,31):
    req.add(d); d += datetime.timedelta(days=1)
print("required days:", len(req))

# find files for years 1991..2014 via glob
found = {}
for year in range(1991, 2015):
    files = fs.glob(f'{base}/sst_{year}*.nc')
    for f in files:
        key = datetime.date(int(f[11:15]), int(f[15:17]), int(f[17:19]))
        found[key] = f
print("found days total:", len(found))
missing = sorted(req - set(found))
print("missing required days:", missing if missing else "none")
extra = sorted(set(found) - req)
print("extra found days (outside req):", extra[:20], "count", len(extra))
