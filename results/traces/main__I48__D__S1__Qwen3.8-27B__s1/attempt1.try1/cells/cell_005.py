import fsspec, os, xarray as xr
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
os.makedirs('/work/data', exist_ok=True)
os.makedirs('/work/output', exist_ok=True)
fs.get(f"{base}/sst_20160601.nc", '/work/data/sst_20160601.nc')
ds = xr.open_dataset('/work/data/sst_20160601.nc', engine='h5netcdf')
print(ds)
ds.close()
