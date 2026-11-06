import xarray as xr
path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
try:
    ds = xr.open_dataset(path, engine="h5netcdf")
    print(ds)
except Exception as e:
    print("h5netcdf failed:", e)
    ds = xr.open_dataset(path)
    print(ds)
