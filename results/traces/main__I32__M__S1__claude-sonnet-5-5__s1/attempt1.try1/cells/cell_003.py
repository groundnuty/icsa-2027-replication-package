import xarray as xr
d='/data/icsa2027_data_20261101T090944Z/s1z'
ds=xr.open_dataset(d+'/sst_20050601.nc',engine='h5netcdf');print(ds)
print(ds.encoding)