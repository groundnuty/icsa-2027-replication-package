import xarray as xr, numpy as np
ds = xr.open_dataset('/work/data/sst_s2.nc', engine="h5netcdf")
print("opened ok")
v = ds['analysed_sst']
print("data obj:", type(v.data))
x = v.data[3647, 250, 440]
print("scalar read:", x, type(x))