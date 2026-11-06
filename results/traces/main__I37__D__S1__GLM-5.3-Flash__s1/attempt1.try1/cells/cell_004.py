import fsspec, os, xarray as xr, numpy as np
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
os.makedirs('/work/tmp', exist_ok=True)
local = '/work/tmp/sample.nc'
fs.get(f'{base}/sst_19920601.nc', local)
ds = xr.open_dataset(local, engine='h5netcdf')
print(ds)
print("---- attrs ----")
for k,v in ds.attrs.items():
    print(k, ":", str(v)[:200])
for c in ds.coords:
    print(c, ds[c].dtype, ds[c].shape, ds[c].attrs)
    if ds[c].size <= 12:
        print("  values:", ds[c].values)
