import fsspec, xarray as xr, os
fs = fsspec.filesystem('onedata')
os.makedirs('/work',exist_ok=True)
fs.get('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc','/work/sst_s2.nc')
fs.get('icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc','/work/sst_19820101.nc')
for p in ['/work/sst_s2.nc','/work/sst_19820101.nc']:
    ds=xr.open_dataset(p,engine='h5netcdf')
    print(ds)
    print('---')