
import xarray as xr
ds = xr.open_dataset('/work/sst_19820101.nc', engine='h5netcdf')
print(ds)
print("\nVariables:", list(ds.variables))
print("\nDims:", dict(ds.sizes))
