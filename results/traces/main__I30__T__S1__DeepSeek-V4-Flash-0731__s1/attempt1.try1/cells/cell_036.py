
import numpy as np
import xarray as xr

# Load mask
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
mhw_mask = ds['mhw'].values
sea_mask = np.load('/tmp/sea_mask.npy')

# Check: any cell with mhw=1 but not a sea cell?
non_sea_mhw = (mhw_mask > 0) & ~sea_mask[np.newaxis, :, :]
print("Non-sea cells with mhw=1:", non_sea_mhw.sum())

# Check: all sea cells that are hot should be in mhw_mask
# Verify land cells are 0
land_mask = ~sea_mask
land_mhw = mhw_mask[:, land_mask]
print("Land cells mhw values:", np.unique(land_mhw))

# Verify the mask values
print("Total mask cells:", mhw_mask.size)
print("MHW cells:", (mhw_mask == 1).sum())
print("Non-MHW cells:", (mhw_mask == 0).sum())
