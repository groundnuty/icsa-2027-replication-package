
import fsspec, xarray as xr, numpy as np
fs = fsspec.filesystem('onedata')
f = fs.open('/icsa2027_data_20261101T090944Z/s1z/sst_20160601.nc','rb')
ds = xr.open_dataset(f, engine='h5netcdf')
print(ds)
print("---attrs---")
for k,v in ds.attrs.items(): print(k,":",v)
f.close()
