import h5py, numpy as np, time, os
local='/work/cache/sst_20090601.nc'
with h5py.File(local,'r') as f:
    print('root keys:', list(f.keys()))
    print('time attrs:', dict(f['time'].attrs))
    print('time values:', f['time'][:])
    print('lat attrs:', dict(f['latitude'].attrs))
    t0=time.time()
    sl = f['analysed_sst'][0, 322:382, 485:544]
    print('h5py slice time', round(time.time()-t0,4), sl.shape, sl.dtype)
    t0=time.time()
    for _ in range(5):
        sl = f['analysed_sst'][0, 322:382, 485:544]
    print('avg slice time', round((time.time()-t0)/5,4))
