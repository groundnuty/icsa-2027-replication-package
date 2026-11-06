
import numpy as np
from datetime import date, timedelta
import json, time

intermediate_dir = 'intermediate'

# Load metadata
with open(f'{intermediate_dir}/metadata.json') as f:
    meta = json.load(f)

baseline_dates = [date.fromisoformat(d) for d in meta['baseline_dates']]
target_dates = [date.fromisoformat(d) for d in meta['target_dates']]

# Load data
threshold_raw = np.load(f'{intermediate_dir}/threshold_raw.npy')
climatology_raw = np.load(f'{intermediate_dir}/climatology_raw.npy')
sea_cells = np.load(f'{intermediate_dir}/sea_cells.npy')
target_sst = np.load(f'{intermediate_dir}/target_sst.npy')

print(f"threshold_raw: {threshold_raw.shape}")
print(f"climatology_raw: {climatology_raw.shape}")

# Smooth with 31-day centered moving average that wraps around the year
def smooth_wrap(arr):
    """Smooth a 366-element array with 31-day centered moving average (wrapping)."""
    # arr shape: (366, n_lat, n_lon)
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

# Verify: check some values
print("Threshold[152] (June 1) sample:", threshold_smooth[152, 350, 413])
print("Climatology[152] (June 1) sample:", climatology_smooth[152, 350, 413])
print("Threshold[59] (Feb 29) sample:", threshold_smooth[59, 350, 413])
print("Climatology[59] (Feb 29) sample:", climatology_smooth[59, 350, 413])

# Check for non-finite values in sea cells
sea_flat = sea_cells.flatten()
n_sea = sea_flat.sum()
print(f"Sea cells: {n_sea}")
for doy in [0, 59, 60, 152, 243]:
    t = threshold_smooth[doy]
    c = climatology_smooth[doy]
    print(f"  doy {doy+1}: threshold NaN count in sea cells: {np.isnan(t[sea_cells]).sum()}/{n_sea}, climatology NaN: {np.isnan(c[sea_cells]).sum()}/{n_sea}")
