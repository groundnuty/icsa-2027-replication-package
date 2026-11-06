import h5py, numpy as np, time, hashlib
p = '/data/icsa2027_data_20261101T090944Z/s1z/sst_20040615.nc'
t0 = time.time()
with h5py.File(p, 'r') as f:
    sub = f['analysed_sst'][0, 196:256, 485:545]
    lat = f['latitude'][196:256]
    lon = f['longitude'][485:545]
t1 = time.time()
print('read time', t1-t0, 's; shape', sub.shape, sub.dtype)
print('n NaN', np.isnan(sub).sum(), 'of', sub.size)
print('SST range', np.nanmin(sub), np.nanmax(sub))
# verify lat/lon consistency across several files
for date in ['19911227','19960229','20030605','20040601','20040831','20000704']:
    with h5py.File(f'/data/icsa2027_data_20261101T090944Z/s1z/sst_{date}.nc','r') as f:
        la = f['latitude'][196:256]; lo = f['longitude'][485:545]
        t = f['time'][:]
    ok = np.array_equal(la, lat) and np.array_equal(lo, lon)
    print(date, 'grid match:', ok, 'time:', t)
