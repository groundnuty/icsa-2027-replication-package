import xarray as xr
ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s1z/sst_20190601.nc', engine='h5netcdf')
print(ds)
print("\nVariables:", list(ds.data_vars))
print("\nCoords:", list(ds.coords))
print("\nDims:", dict(ds.sizes))
