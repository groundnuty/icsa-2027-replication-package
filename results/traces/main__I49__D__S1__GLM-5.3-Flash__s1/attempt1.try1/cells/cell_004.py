import fsspec, os, xarray as xr
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
os.makedirs('/work/probe', exist_ok=True)
for p in ['sst_19920101.nc','sst_20190601.nc']:
    fs.get(f'{base}/{p}', f'/work/probe/{p}')
ds = xr.open_dataset('/work/probe/sst_19920101.nc', engine='h5netcdf')
print(ds)
print("--- attrs:", ds.attrs)
