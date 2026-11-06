import h5py, numpy as np, time, os
i0, i1, j0, j1 = 196, 256, 485, 545
t0 = time.time()
with h5py.File('/work/sst_s2.nc','r') as f:
    dvar = f['analysed_sst']
    n = dvar.shape[0]
    data = np.empty((n, i1-i0, j1-j0), dtype=np.float32)
    # time a sample of 60 slices
    tt = time.time()
    for k in range(60):
        data[k] = dvar[k, i0:i1, j0:j1]
    dt = time.time()-tt
    print('60 slices in %.2fs -> est full %.0fs' % (dt, dt/60*n))
    for k in range(60, n):
        data[k] = dvar[k, i0:i1, j0:j1]
print('full read %.1fs' % (time.time()-t0))
np.save('/work/region_cube.npy', data)
print('saved', data.shape, data.dtype, os.path.getsize('/work/region_cube.npy'))
print('finite frac overall:', np.isfinite(data).mean())
print('global min/max region:', np.nanmin(data), np.nanmax(data))