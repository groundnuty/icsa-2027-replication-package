import numpy as np

# Check dtypes
base_sst_sea = np.load('/tmp/base_sst_sea.npy')
threshold_smooth = np.load('/tmp/threshold_smooth.npy')
clim_smooth = np.load('/tmp/clim_smooth.npy')
target_sst = np.load('/tmp/target_sst.npy')

print(f"base_sst_sea dtype: {base_sst_sea.dtype}")
print(f"threshold_smooth dtype: {threshold_smooth.dtype}")
print(f"clim_smooth dtype: {clim_smooth.dtype}")
print(f"target_sst dtype: {target_sst.dtype}")

# Also check hot computation
print(f"\ntarget_sst is float64: {target_sst.dtype == np.float64}")
