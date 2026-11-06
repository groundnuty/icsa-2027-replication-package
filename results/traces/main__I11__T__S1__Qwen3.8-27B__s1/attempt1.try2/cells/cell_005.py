
import fsspec, xarray as xr
fs = fsspec.filesystem('onedata')
base = '/icsa2027_data_20261101T090944Z/s1z/'
with fs.open(base + "sst_20210601.nc", "rb") as f:
    ds = xr.open_dataset(f, engine="h5netcdf")
print(ds)
print()
for k, v in ds.attrs.items():
    print(k, "=", str(v)[:200])
