import numpy as np, xarray as xr
ds = xr.open_dataset('/work/data/sst_19911227.nc', engine='h5netcdf')
print(ds)
v = ds['analysed_sst']
print("v dims:", v.dims, "v.shape:", v.shape, type(v.values))
vv = v.values
print("vv shape:", vv.shape, vv.ndim)
ds.close()
