import fsspec
fs = fsspec.filesystem('onedata')
import datetime as dt
d = dt.date(1982,1,1); end = dt.date(2023,12,31)
missing = []
step = dt.timedelta(days=1)
# sample check every 30 days plus edges
checks = [dt.date(1982,1,1), dt.date(1992,1,1), dt.date(1992,12,31), dt.date(2002,12,31), dt.date(2003,1,5), dt.date(2010,6,1), dt.date(2010,8,31), dt.date(2023,12,31), dt.date(1984,9,27), dt.date(1984,9,28)]
while d <= end:
    checks.append(d); d += dt.timedelta(days=30)
for c in sorted(set(checks)):
    p = f'icsa2027_data_20261101T090944Z/s1z/sst_{c:%Y%m%d}.nc'
    if not fs.exists(p):
        missing.append(str(c))
print('missing count in sample:', len(missing))
print(missing[:40])
