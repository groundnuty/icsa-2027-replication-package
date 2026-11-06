import xarray as xr
p = '/data/icsa2027_data_20261101T090944Z/s1z/sst_20040615.nc'
ds = xr.open_dataset(p, engine='h5netcdf')
print(ds)
print()
for v in ds.variables:
    print(v, ds[v].dtype, ds[v].shape, dict(ds[v].attrs))
