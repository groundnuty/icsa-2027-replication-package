import numpy as np, xarray as xr
ds = xr.open_dataset('/work/data/sst_s2.nc', engine="h5netcdf")
v = ds['analysed_sst']
print("v.data type:", type(v.data))
x = v.data[3647, 250, 440]
print("scalar read:", x, type(x))
y = v.data[3647, 250, 440:443]
print("slice read:", y, y.shape)