import xarray as xr

sample_file = '/data/icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc'
ds = xr.open_dataset(sample_file, engine="h5netcdf")
print(ds)
