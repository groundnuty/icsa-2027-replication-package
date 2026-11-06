
import numpy as np

# Load raw threshold and climatology
threshold_raw = np.load('/work/threshold_raw.npy')
climatology_raw = np.load('/work/climatology_raw.npy')

print("threshold_raw shape:", threshold_raw.shape)
print("climatology_raw shape:", climatology_raw.shape)

# Apply 31-day centered moving mean wrapping around year
def smooth_366(arr):
    """Apply 31-day centered moving mean wrapping around year.
    arr shape: (366, lat, lon)"""
    n = 366
    result = np.zeros_like(arr)
    for i in range(n):
        indices = [(i + offset) % n for offset in range(-15, 16)]
        result[i] = np.mean(arr[indices], axis=0)
    return result

print("Smoothing threshold...")
threshold_smooth = smooth_366(threshold_raw)
print("Smoothing climatology...")
climatology_smooth = smooth_366(climatology_raw)

print("Smoothing done")

# Check for NaN
n_sea = np.sum(~np.isnan(threshold_smooth[0]))
print("Non-NaN threshold values in first day:", n_sea)

# Verify day 60 value
print("threshold_smooth[58, 5, 5] (doy 59):", threshold_smooth[58, 5, 5])
print("threshold_smooth[59, 5, 5] (doy 60):", threshold_smooth[59, 5, 5])
print("threshold_smooth[60, 5, 5] (doy 61):", threshold_smooth[60, 5, 5])

# Check no NaN in sea cells
sea_cells = np.all(np.isfinite(np.load('/work/target_sst.npy')), axis=0)
for i in range(366):
    assert not np.any(np.isnan(threshold_smooth[i, sea_cells])), f"NaN threshold at smoothed doy {i+1}"
    assert not np.any(np.isnan(climatology_smooth[i, sea_cells])), f"NaN climatology at smoothed doy {i+1}"

print("All smoothed values are finite for sea cells")

# Save smoothed threshold and climatology
np.save('/work/threshold_smooth.npy', threshold_smooth)
np.save('/work/climatology_smooth.npy', climatology_smooth)
print("Saved smoothed threshold and climatology")
