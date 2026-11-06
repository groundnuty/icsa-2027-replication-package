import fsspec, pickle, os
fs = fsspec.filesystem('onedata')
path = "icsa2027_data_20261101T090944Z/s1z"
entries = fs.ls(path)
names = [e.split('/')[-1] for e in entries if e.endswith('.nc')]
print("total files:", len(names))
import re
dates = set()
bad = 0
for n in names:
    m = re.fullmatch(r'sst_(\d{8})\.nc', n)
    if m:
        dates.add(m.group(1))
    else:
        bad += 1
print("unique dates:", len(dates), "bad names:", bad)
ds = sorted(dates)
print("first:", ds[:5], "last:", ds[-5:])

# required dates
import datetime as dt
def dstr(d): return d.strftime("%Y%m%d")
needed = set()
# baseline window: 1991-12-27 .. 2003-01-05
d0 = dt.date(1991,12,27); d1 = dt.date(2003,1,5)
cur = d0
while cur <= d1:
    needed.add(dstr(cur)); cur += dt.timedelta(days=1)
# target
t0 = dt.date(2012,6,1); t1 = dt.date(2012,8,31)
cur = t0
while cur <= t1:
    needed.add(dstr(cur)); cur += dt.timedelta(days=1)
missing = sorted(needed - dates)
print("needed:", len(needed), "missing:", len(missing))
print("missing list:", missing[:50])
pickle.dump({"names": names, "dates": dates}, open("/tmp/dataset_files.pkl","wb"))