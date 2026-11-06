
import numpy as np

threshold_smooth = np.load('/tmp/threshold_smooth.npy')
climatology_smooth = np.load('/tmp/climatology_smooth.npy')

# Check a few sea cells
sea_mask = np.load('/tmp/sea_mask.npy')
sea_indices = np.where(sea_mask)
i, j = sea_indices[0][0], sea_indices[1][0]
print(f"First sea cell at ({i},{j})")
print(f"Threshold day 153: {threshold_smooth[153, i, j]:.4f}")
print(f"Climatology day 153: {climatology_smooth[153, i, j]:.4f}")
print(f"Threshold day 200: {threshold_smooth[200, i, j]:.4f}")
print(f"Climatology day 200: {climatology_smooth[200, i, j]:.4f}")
print(f"Threshold day 244: {threshold_smooth[244, i, j]:.4f}")
print(f"Climatology day 244: {climatology_smooth[244, i, j]:.4f}")

# Check all sea cells have threshold > climatology
diff = threshold_smooth - climatology_smooth
sea_diff = diff[153:245, sea_mask]
print(f"Threshold > climatology for all sea cells and target days: {np.all(sea_diff > 0)}")

# Check range of thresholds for target days
print(f"Threshold range for target days (sea cells): {np.nanmin(threshold_smooth[153:245, sea_mask]):.4f} to {np.nanmax(threshold_smooth[153:245, sea_mask]):.4f}")
print(f"Climatology range for target days (sea cells): {np.nanmin(climatology_smooth[153:245, sea_mask]):.4f} to {np.nanmax(climatology_smooth[153:245, sea_mask]):.4f}")

# Verify a few specific values manually
# Check the raw threshold for day 153
threshold_raw = np.load('/tmp/threshold_raw.npy')
print(f"\nRaw threshold day 153 at cell ({i},{j}): {threshold_raw[153, i, j]:.4f}")
print(f"Raw climatology day 153 at cell ({i},{j}): {np.load('/tmp/climatology_raw.npy')[153, i, j]:.4f}")
