import fsspec, xarray as xr, numpy as np, time
fs = fsspec.filesystem('onedata')
p = 'icsa2027_data_20261101T090944Z/s1z'
t0 = time.time()
f = fs.open(p + '/sst_20210601.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
sub = ds['analysed_sst'][0, 109:169, 373:433].values.astype('float64')
print('one read+decode: %.2f s' % (time.time()-t0), sub.shape, sub.dtype, np.nanmin(sub), np.nanmax(sub))
# quick loop test of 5 sequential reads
t0 = time.time()
for d in ['19920101','19920102','19920103','19920104','19920105']:
    g = xr.open_dataset(fs.open(p + f'/sst_{d}.nc','rb'), engine='h5netcdf')
    v = g['analysed_sst'][0, 109:169, 373:433].values.astype('float64')
    g.close()
print('5 more reads: %.2f s' % (time.time()-t0))
