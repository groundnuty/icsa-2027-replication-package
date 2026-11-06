
import xarray as xr
import numpy as np

# Open one file to see the structure
ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s1z/sst_20140601.nc', engine='h5netcdf')
print(ds)
print("\n--- Variables ---")
for var in ds.variables:
    print(f"{var}: {ds[var].shape}, dtype={ds[var].dtype}")
    print(f"  attrs: {ds[var].attrs}")
