
import fsspec, xarray, time, numpy as np
fs = fsspec.filesystem('onedata')
t0 = time.time()
f = fs.open('/icsa2027_data_20261101T090944Z/s1z/sst_20100602.nc','rb')
ds = xarray.open_dataset(f, engine='h5netcdf')
arr = ds['analysed_sst'].values
t1 = time.time()
print('single file read+load:', round(t1-t0,2), 's', arr.shape, arr.dtype, round(float(np.nanmean(arr)),3))
print('seekable:', f.seekable())
ds.close(); f.close()
