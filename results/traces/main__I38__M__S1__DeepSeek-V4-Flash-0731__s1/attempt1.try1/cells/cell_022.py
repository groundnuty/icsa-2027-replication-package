
import numpy as np
from datetime import date, timedelta
import json

intermediate_dir = 'intermediate'

# Load data
threshold_smooth = np.load(f'{intermediate_dir}/threshold_smooth.npy')
climatology_smooth = np.load(f'{intermediate_dir}/climatology_smooth.npy')
sea_cells = np.load(f'{intermediate_dir}/sea_cells.npy')
mhw_mask = np.load(f'{intermediate_dir}/mhw_mask.npy')
target_sst = np.load(f'{intermediate_dir}/target_sst.npy')

# Check some values
# Find a sea cell and look at its data
sea_indices = np.argwhere(sea_cells)
print(f"First 5 sea cell indices: {sea_indices[:5]}")

# For the first sea cell, look at target SST and threshold
la, lo = sea_indices[0]
print(f"\nCell ({la}, {lo})")
print(f"  Target SST (first 10 days): {target_sst[:10, la, lo]}")
print(f"  Threshold (first 10 days): {threshold_smooth[[152,153,154,155,156,157,158,159,160,161], la, lo]}")
print(f"  Hot (first 10 days): {mhw_mask[:10, la, lo]}")
