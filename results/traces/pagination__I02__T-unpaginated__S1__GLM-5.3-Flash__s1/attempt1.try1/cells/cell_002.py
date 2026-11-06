import fsspec
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
# check boundary files exist
for d in ['19911227','19911231','19920101','20021231','20030101','20030105','20040601','20040831']:
    p = f'{base}/sst_{d}.nc'
    print(d, fs.exists(p))
# count files from 1991-12-27 to 2003-01-05 and 2004-06-01 to 2004-08-31
import datetime as dt
def daterange(a,b):
    d=a
    while d<=b:
        yield d; d+=dt.timedelta(days=1)
need1 = list(daterange(dt.date(1991,12,27), dt.date(2003,1,5)))
need2 = list(daterange(dt.date(2004,6,1), dt.date(2004,8,31)))
print(len(need1), len(need2))
missing = [d for d in need1+need2 if not fs.exists(f"{base}/sst_{d:%Y%m%d}.nc")]
print("missing:", missing[:20], len(missing))
