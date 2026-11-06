import xarray as xr
import numpy as np
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
print(ds)
print("---- attrs ----")
for k,v in ds.attrs.items():
    print(k, ":", str(v)[:200])
