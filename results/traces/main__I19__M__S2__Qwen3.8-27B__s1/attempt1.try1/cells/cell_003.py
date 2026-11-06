import xarray as xr
path = '/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds = xr.open_dataset(path, engine="h5netcdf")
print(ds)
print("---attrs---")
for k,v in ds.attrs.items():
    print(k, "=", v)
