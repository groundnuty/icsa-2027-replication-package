
import xarray as xr
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
print(ds)
print("\nVariables:", list(ds.variables))
print("\nDims:", dict(ds.dims))
print("\nCoords:", list(ds.coords))
