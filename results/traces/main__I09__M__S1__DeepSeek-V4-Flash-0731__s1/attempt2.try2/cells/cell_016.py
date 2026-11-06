
import numpy as np

# Load data
baseline_sst = np.load('/tmp/baseline_sst.npy')
sea_cells = np.load('/tmp/sea_cells.npy')
doy_pool_indices = np.load('/tmp/doy_pool_indices.npy', allow_pickle=True)

n_lat, n_lon = sea_cells.shape
print(f"baseline_sst shape: {baseline_sst.shape}")
print(f"doy_pool_indices length: {len(doy_pool_indices)}")
print(f"doy_pool_indices[0] (doy 1): {len(doy_pool_indices[0])} entries")
print(f"doy_pool_indices[365] (doy 366): {len(doy_pool_indices[365])} entries")
print(f"doy_pool_indices[58] (doy 59): {len(doy_pool_indices[58])} entries")
print(f"doy_pool_indices[59] (doy 60): {len(doy_pool_indices[59])} entries")
