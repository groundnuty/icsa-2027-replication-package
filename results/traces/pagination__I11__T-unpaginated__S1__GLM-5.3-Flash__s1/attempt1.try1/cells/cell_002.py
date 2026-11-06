import fsspec, numpy as np
fs = fsspec.filesystem('onedata')
p = 'icsa2027_data_20261101T090944Z/s1z'
entries = fs.ls(p)
names = [e.split('/')[-1] for e in entries]
print('first:', names[0], 'last:', names[-1], 'count:', len(names))
import re
dates = sorted(n[4:12] for n in names if re.fullmatch(r'sst_\d{8}\.nc', n))
print('min date', dates[0], 'max date', dates[-1], 'n', len(dates))
# check continuity
import datetime as dt
ds = [dt.datetime.strptime(d, '%Y%m%d').date() for d in dates]
missing = []
cur = ds[0]
while cur <= ds[-1]:
    if cur not in set(ds): missing.append(str(cur))
    cur += dt.timedelta(days=1)
print('missing days:', len(missing), missing[:20])
# check presence of needed boundary days
for d in ['19911227','19911231','19920101','20021231','20030101','20030105','20210601','20210831','20200229']:
    print(d, ('sst_%s.nc'%d) in set(names))
