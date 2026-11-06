import fsspec, re
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
items = fs.ls(base)
print("total files:", len(items))
names = sorted(i.split('/')[-1] for i in items)
dates = [n.replace('sst_','').replace('.nc','') for n in names]
print("first:", dates[0], "last:", dates[-1])
# check expected count: 1982-01-01 to ... 
import datetime as dt
first = dt.date(1982,1,1)
last = dt.date(*[int(x) for x in dates[-1][0:4]+dates[-1][4:6]+dates[-1][6:8]])
print("expected:", (last-first).days+1)
# check for missing
have = set(dates)
exp = set()
d = first
while d <= last:
    exp.add(d.strftime('%Y%m%d'))
    d += dt.timedelta(days=1)
missing = sorted(exp - have)
print("missing count:", len(missing), missing[:10])
