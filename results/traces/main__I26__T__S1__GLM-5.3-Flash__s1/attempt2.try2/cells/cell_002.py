import fsspec, os
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s1z'
entries = fs.ls(path, detail=False)
names = sorted(entries)
print(len(names))
print(names[0], names[-1])
# check continuity
import re
dates = [n.split('_')[1][:-3] for n in names]
print(dates[0], dates[-1])
# find missing dates
import datetime as dt
d0 = dt.date(1982,1,1)
d1 = dt.date.fromisoformat(dates[-1])
ndays = (d1-d0).days+1
allset = set(dates)
missing = []
for i in range(ndays):
    dd = d0+dt.timedelta(days=i)
    if dd.isoformat() not in allset:
        missing.append(dd.isoformat())
print('missing count', len(missing), missing[:10])
