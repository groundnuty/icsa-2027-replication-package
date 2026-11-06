
import numpy as np
from datetime import date, timedelta
import json, time

intermediate_dir = 'intermediate'

# Load metadata
with open(f'{intermediate_dir}/metadata.json') as f:
    meta = json.load(f)

# Load data
threshold_raw = np.load(f'{intermediate_dir}/threshold_raw.npy')
climatology_raw = np.load(f'{intermediate_dir}/climatology_raw.npy')
sea_cells = np.load(f'{intermediate_dir}/sea_cells.npy')
target_sst = np.load(f'{intermediate_dir}/target_sst.npy')

print(f"threshold_raw: {threshold_raw.shape}")

# Smooth with 31-day centered moving average that wraps around the year
def smooth_wrap(arr):
    """Smooth a 366-element array with 31-day centered moving average (wrapping)."""
    half = 15
    result = np.zeros_like(arr)
    for d in range(366):
        indices = [(d + i) % 366 for i in range(-half, half+1)]
        result[d] = np.mean(arr[indices], axis=0)
    return result

t0 = time.time()
threshold_smooth = smooth_wrap(threshold_raw)
print(f"Threshold smoothing took {time.time()-t0:.1f}s")

t0 = time.time()
climatology_smooth = smooth_wrap(climatology_raw)
print(f"Climatology smoothing took {time.time()-t0:.1f}s")

np.save(f'{intermediate_dir}/threshold_smooth.npy', threshold_smooth)
np.save(f'{intermediate_dir}/climatology_smooth.npy', climatology_smooth)

# Verify: check some values (using local indices, e.g., cell 0,0)
print("Threshold[152] (June 1) cell[0,0]:", threshold_smooth[152, 0, 0])
print("Climatology[152] (June 1) cell[0,0]:", climatology_smooth[152, 0, 0])
print("Threshold[59] (Feb 29) cell[0,0]:", threshold_smooth[59, 0, 0])
print("Climatology[59] (Feb 29) cell[0,0]:", climatology_smooth[59, 0, 0])

# Check for non-finite values in sea cells
n_sea = sea_cells.sum()
print(f"Sea cells: {n_sea}")
for doy in [0, 59, 60, 152, 243]:
    t = threshold_smooth[doy]
    c = climatology_smooth[doy]
    print(f"  doy {doy+1}: threshold NaN in sea cells: {np.isnan(t[sea_cells]).sum()}/{n_sea}, climatology NaN: {np.isnan(c[sea_cells]).sum()}/{n_sea}")
