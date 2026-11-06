import fsspec, os, xarray as xr
fs = fsspec.filesystem('onedata')
os.makedirs('/work/d',exist_ok=True)
fs.get('icsa2027_data_20261101T090944Z/s1z/sst_19920101.nc','/work/d/sst_19920101.nc')
ds=xr.open_dataset('/work/d/sst_19920101.nc',engine='h5netcdf')
print(ds)
