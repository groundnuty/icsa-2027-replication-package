
import numpy as np

# Load intermediate results
threshold_raw = np.load('output/threshold_raw.npy')
climatology_raw = np.load('output/climatology_raw.npy')

# Set day 60 (index 59) to mean of days 59 and 61 (indices 58 and 60)
threshold_raw[59] = (threshold_raw[58] + threshold_raw[60]) / 2.0
climatology_raw[59] = (climatology_raw[58] + climatology_raw[60]) / 2.0

# Apply 31-day centered moving mean wrapping around (366 days)
def smooth_366(arr):
    """Smooth a (366, n_lat, n_lon) array with a 31-day centered moving mean wrapping around."""
    result = np.zeros_like(arr)
    for i in range(366):
        # Days i-15 to i+15 (mod 366)
        indices = [(i + j) % 366 for j in range(-15, 16)]
        # Take the mean
        result[i] = np.nanmean(arr[indices], axis=0)
    return result

# Apply smoothing
threshold_smooth = smooth_366(threshold_raw)
climatology_smooth = smooth_366(climatology_raw)

print("Applied smoothing")
print(f"Threshold day 1, cell [30,30] (raw): {threshold_raw[0, 30, 30]:.4f}, smooth: {threshold_smooth[0, 30, 30]:.4f}")
print(f"Clim day 1, cell [30,30] (raw): {climatology_raw[0, 30, 30]:.4f}, smooth: {climatology_smooth[0, 30, 30]:.4f}")

# Check for NaN in sea cells
# First, identify sea cells (non-NaN threshold for all days)
sea_mask = ~np.isnan(threshold_smooth).all(axis=0)
print(f"Sea cells: {sea_mask.sum()} out of {60*60}")

# Check if any sea cell has NaN in the smoothed threshold
for i in range(366):
    for lat in range(60):
        for lon in range(60):
            if sea_mask[lat, lon] and np.isnan(threshold_smooth[i, lat, lon]):
                print(f"NaN in threshold at day {i+1}, cell ({lat},{lon})")
                break
        else:
            continue
        break
    else:
        continue
    break
else:
    print("No NaN in threshold for sea cells")

# Save smoothed results
np.save('output/threshold_smooth.npy', threshold_smooth)
np.save('output/climatology_smooth.npy', climatology_smooth)
np.save('output/sea_mask.npy', sea_mask)
print("Saved smoothed results")
