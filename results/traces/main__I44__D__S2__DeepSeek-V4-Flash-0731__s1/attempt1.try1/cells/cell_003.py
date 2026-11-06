
import xarray as xr
import numpy as np

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
print(ds)
print("\nDimensions:", dict(ds.sizes))
print("\nCoordinates:")
for name, coord in ds.coords.items():
    print(f"  {name}: {coord.values}")
