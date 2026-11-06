
import fsspec, re
fs = fsspec.filesystem('onedata')
files = fs.ls('/icsa2027_data_20261101T090944Z/s1z')
names = sorted(f.split('/')[-1] for f in files)
print(len(names), names[0], names[-1])
# check the ones we need
need = set()
import datetime as dt
d = dt.date(1991,12,27)
while d <= dt.date(2003,1,5):
    need.add(f"sst_{d.strftime('%Y%m%d')}.nc")
    d += dt.timedelta(days=1)
d = dt.date(2015,6,1)
while d <= dt.date(2015,8,31):
    need.add(f"sst_{d.strftime('%Y%m%d')}.nc")
    d += dt.timedelta(days=1)
missing = need - set(names)
print("missing:", sorted(missing)[:20], len(missing))
