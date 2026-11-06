
import numpy as np

mhw_mask = np.load('/work/mhw_mask.npy')
target_arr = np.load('/work/target_arr.npy')

sea_mask = np.all(np.isfinite(target_arr), axis=0)
land_mask = ~sea_mask

# Check that land cells have mhw = 0 everywhere
land_mhw = mhw_mask[:, land_mask]
print("Land cells MHW sum:", land_mhw.sum())

# Check that sea cells have MHW values
sea_mhw = mhw_mask[:, sea_mask]
print("Sea cells MHW sum:", sea_mhw.sum())
print("Total MHW:", mhw_mask.sum())
