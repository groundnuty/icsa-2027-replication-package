import xarray as xr

# Try to open one file to check coordinates and variable names
sample_file = "/data/icsa2027_data_20261101T090944Z/s1z/sst_20231231.nc"
ds = xr.open_dataset(sample_file, engine="h5netcdf")
print(ds)
