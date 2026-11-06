import fsspec, time
fs = fsspec.filesystem('onedata')
base='/icsa2027_data_20261101T090944Z/s1z'
t0=time.time()
try:
    g = fs.glob(base+'/sst_1992*.nc')
    print('glob OK n=', len(g), 'time', round(time.time()-t0,2))
except Exception as ex:
    print('glob err', repr(ex)[:200])
t0=time.time()
try:
    g2 = fs.glob(base+'/sst_*.nc')
    print('glob all OK n=', len(g2), 'time', round(time.time()-t0,2))
    print('first', g2[0].split('/')[-1], 'last', g2[-1].split('/')[-1])
except Exception as ex:
    print('glob all err', repr(ex)[:200])
