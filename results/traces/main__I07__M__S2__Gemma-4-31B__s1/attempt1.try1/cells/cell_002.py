import xarray as xr

ds_path = '/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds = xr.open_dataset(ds_path, engine="h5netcdf")
print(ds)
