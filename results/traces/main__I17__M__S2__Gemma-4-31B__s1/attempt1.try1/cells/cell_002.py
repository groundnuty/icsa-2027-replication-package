import xarray as xr

FILE_PATH = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(FILE_PATH, engine="h5netcdf")
print(ds)
