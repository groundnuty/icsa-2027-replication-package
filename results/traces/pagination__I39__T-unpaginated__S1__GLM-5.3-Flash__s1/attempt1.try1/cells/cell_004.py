import fsspec, os
fs = fsspec.filesystem('onedata')
entries = fs.ls('icsa2027_data_20261101T090944Z/s1z', detail=True)
base = set(os.path.basename(e['name']) for e in entries)
need = ['19911227','19911231','19920229','19930228','20030105','20100601','20100831','20100531','20100901','20021231','19920101','20100630']
for d in need:
    print(d, f'sst_{d}.nc' in base)
print(len(base))
# gap check between 1991-12-27 and 2003-01-05 and 2010-06-01..2010-08-31
import datetime as dt
d0 = dt.date(1991,12,27); d1 = dt.date(2003,1,5)
missing = []
cur = d0
while cur <= d1:
    if f'sst_{cur:%Y%m%d}.nc' not in base:
        missing.append(f'{cur:%Y%m%d}')
    cur += dt.timedelta(days=1)
print('missing in 1991-12-27..2003-01-05:', len(missing), missing[:20])
d0 = dt.date(2010,6,1); d1 = dt.date(2010,8,31)
missing2 = []
cur = d0
while cur <= d1:
    if f'sst_{cur:%Y%m%d}.nc' not in base:
        missing2.append(f'{cur:%Y%m%d}')
    cur += dt.timedelta(days=1)
print('missing in target:', len(missing2), missing2[:20])
