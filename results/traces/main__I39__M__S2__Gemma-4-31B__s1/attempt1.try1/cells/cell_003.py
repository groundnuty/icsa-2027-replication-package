import xarray as xr
dataset_path = '/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds = xr.open_dataset(dataset_path, engine="h5netcdf")
print(ds.data_vars)
