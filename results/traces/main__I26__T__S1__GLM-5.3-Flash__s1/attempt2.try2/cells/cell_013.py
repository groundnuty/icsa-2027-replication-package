import fsspec, json, os, datetime as dt, time
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
t0=time.time()
try:
    g = fs.glob(base + '/sst_1992*.nc')
    print('glob works:', len(g), 'time', time.time()-t0)
    print(g[0], g[-1])
except Exception as e:
    print('glob ERR', type(e).__name__, str(e)[:300])
