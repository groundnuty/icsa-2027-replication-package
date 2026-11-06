import xarray as xr
d = "/data/icsa2027_data_20261101T090944Z/s1z"
p = d + "/sst_20130601.nc"
ds = xr.open_dataset(p, engine="h5netcdf")
print(ds)
print("---attrs---")
for k,v in ds.attrs.items():
    print(k, ":", str(v)[:200])
