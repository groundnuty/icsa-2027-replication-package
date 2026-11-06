import fsspec, io, h5py, numpy as np, random
from datetime import date, timedelta

dat = np.load('/tmp/sst_data.npz')
master = dat['master']; target = dat['target']
fs = fsspec.filesystem('onedata')
BASE='/icsa2027_data_20261101T090944Z/s1z'

def daterange(a,b):
    o=[]
    while a<=b: o.append(a); a+=timedelta(days=1)
    return o
base_dates = daterange(date(1991,12,27), date(2003,1,5))
tgt_dates  = daterange(date(2021,6,1), date(2021,8,31))

# independent spot check: 6 random dates from both spans
random.seed(42)
checks = random.sample(range(4028), 4) + random.sample(range(92), 2)
maxdiff = 0
for c in checks:
    if c < 4028:
        dt = base_dates[c]; stored = master[c]
        arr = stored
    else:
        dt = tgt_dates[c-4028]; stored = target[c-4028]
        arr = stored
    name = 'sst_%04d%02d%02d.nc' % (dt.year, dt.month, dt.day)
    with fs.open(BASE+'/'+name, 'rb') as f:
        h = h5py.File(io.BytesIO(f.read()), 'r')
    v = h['analysed_sst'][0, 404:464, 559:619][:].astype(np.float64)
    h.close()
    d2 = np.nanmax(np.abs(v - arr))
    print(dt, "max abs diff vs stored:", d2)
    maxdiff = max(maxdiff, d2)
print("OVERALL maxdiff:", maxdiff)
