import fsspec, os, xarray as xr
fs = fsspec.filesystem('onedata')
base='icsa2027_data_20261101T090944Z/s1z'
os.makedirs('/work/t',exist_ok=True)
fs.get(f'{base}/sst_20040601.nc','/work/t/a.nc')
ds=xr.open_dataset('/work/t/a.nc',engine='h5netcdf')
print(ds)
print(ds.attrs)