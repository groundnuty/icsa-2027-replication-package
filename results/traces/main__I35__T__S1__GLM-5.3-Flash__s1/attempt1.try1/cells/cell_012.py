import os, shutil, datetime as dt, time
print('disk:', shutil.disk_usage('/work'))
# date lists
def daterange(a,b):
    d=a; out=[]
    while d<=b:
        out.append(d); d+=dt.timedelta(days=1)
    return out
ext = daterange(dt.date(1991,12,27), dt.date(2003,1,5))
tgt = daterange(dt.date(2009,6,1), dt.date(2009,8,31))
print('ext days:', len(ext), ext[0], ext[-1])
print('tgt days:', len(tgt), tgt[0], tgt[-1])
# quick existence probe of ext endpoints
import fsspec
fs = fsspec.filesystem('onedata')
base='/icsa2027_data_20261101T090944Z/s1z'
for probe in ['sst_19911227.nc','sst_19911231.nc','sst_20030101.nc','sst_20030105.nc','sst_19920229.nc','sst_20000229.nc']:
    try:
        fs.info(f'{base}/{probe}'); print(probe,'OK')
    except Exception as e:
        print(probe,'MISSING')
