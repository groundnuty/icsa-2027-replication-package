import xarray as xr
ds = xr.open_dataset('/work/sst_s2.nc', engine="h5netcdf")
v = ds['analysed_sst']
print(v.attrs)
print()
print(ds['time'].values[:5])
print(ds['time'].values[-5:])
import numpy as np
# check a slice of data values
print(ds['analysed_sst'].isel(time=0).values[:10,:5])
ds.close()
