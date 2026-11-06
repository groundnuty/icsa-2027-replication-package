
import numpy as np
import xarray as xr

# Verify that mhw_mask matches the computed mask
mhw_mask = np.load('mhw_mask.npy')
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
mask_from_nc = ds['mhw'].values
ds.close()
print(f"Mask match: {np.array_equal(mhw_mask.astype(np.uint8), mask_from_nc)}")
print(f"Mask from npy sum: {mhw_mask.sum()}")
print(f"Mask from nc sum: {mask_from_nc.sum()}")
