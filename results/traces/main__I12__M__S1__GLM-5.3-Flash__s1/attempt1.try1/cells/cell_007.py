import h5py, numpy as np, os, datetime as dt, sys
DIR = '/data/icsa2027_data_20261101T090944Z/s1z'
import numpy
print('numpy', numpy.__version__, 'h5py ok')
# check time value vs filename on several files
for name in ['sst_19910227.nc','sst_19960229.nc','sst_20030105.nc','sst_20090601.nc','sst_20090831.nc']:
    p = os.path.join(DIR, name)
    with h5py.File(p,'r') as f:
        t = f['time'][:]
        a = f['analysed_sst']
        sub = a[0,130:190,78:138]
    secs = int(t[0])
    d = dt.date(1981,1,1) + dt.timedelta(seconds=secs)
    print(name, '->', d, 'region shape', sub.shape, 'finite frac', np.isfinite(sub).mean().round(4), 'min/max', np.nanmin(sub).round(3), np.nanmax(sub).round(3))
# writability of sandbox dirs
for d in ['/tmp', '.', '/data']:
    try:
        testp = os.path.join(d, '_wtest')
        with open(testp,'w') as fh: fh.write('x')
        os.remove(testp); print(d, 'writable')
    except Exception as e:
        print(d, 'NOT writable:', e)
