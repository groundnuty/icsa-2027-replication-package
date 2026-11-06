import fsspec, numpy as np, h5netcdf, time

fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
nc = h5netcdf.File(f, 'r')
v = nc['analysed_sst']

t0 = time.time()
a = np.asarray(v[0, :, :])
print("full chunk read:", a.shape, a.dtype, "secs:", round(time.time()-t0, 2))
print("finite frac:", np.isfinite(a).mean())
print("range:", np.nanmin(a), np.nanmax(a))
