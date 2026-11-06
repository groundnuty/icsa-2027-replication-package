
import fsspec, io, time, numpy as np, xarray as xr
fs = fsspec.filesystem('onedata')
base='/icsa2027_data_20261101T090944Z/s1z/'
t0=time.time()
raw = fs.cat_file(base+'sst_19930615.nc')
t1=time.time()
ds = xr.open_dataset(io.BytesIO(raw), engine='h5netcdf')
arr = ds.analysed_sst.values
t2=time.time()
sub = arr[0, 204:264, 63:123].astype(np.float64)
t3=time.time()
print("download %.3f s, parse full %.3f s, slice %.3f s" % (t1-t0, t2-t1, t3-t2))
print("finite in region:", np.isfinite(sub).sum(), "of", sub.size)
ds.close()
