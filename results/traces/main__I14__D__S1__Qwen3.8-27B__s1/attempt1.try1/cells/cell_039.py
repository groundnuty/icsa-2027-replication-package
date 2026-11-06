import xarray as xr
ds = xr.open_dataset('/work/data/sst_s2.nc', engine="h5netcdf")
print("opened ok")
v = ds['analysed_sst']
print("data obj:", type(v.data))