from datetime import date, timedelta
import numpy as np

# Load the previously computed data
# I need to reload everything since the sandbox state persists
# Let me check what's in memory

# Actually, let me check if baseline_sst and related are still in memory
try:
    print(f"baseline_sst shape: {baseline_sst.shape}")
    print(f"all_loaded_dates count: {len(all_loaded_dates)}")
except NameError:
    print("Variables not in memory, need to reload")

# Let me check the key variables
print(f"doy_to_pool_indices: {len(doy_to_pool_indices)}")
print(f"date_to_idx count: {len(date_to_idx)}")
