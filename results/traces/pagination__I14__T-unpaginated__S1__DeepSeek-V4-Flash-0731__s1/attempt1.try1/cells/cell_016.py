
import numpy as np

# Load smoothed data
threshold_smooth = np.load('threshold_smooth.npy')
climatology_smooth = np.load('climatology_smooth.npy')

print(f"Threshold shape: {threshold_smooth.shape}")
print(f"Climatology shape: {climatology_smooth.shape}")

# Verify a few values (valid indices are 0-59 for lat and 0-59 for lon)
# Let's check cell at (20, 30) - should be a sea cell
print(f"\nThreshold[180] (day 181) at (20, 30): {threshold_smooth[180, 20, 30]}")
print(f"Climatology[180] (day 181) at (20, 30): {climatology_smooth[180, 20, 30]}")

# Check for NaN in sea cells
sea_mask = np.load('sea_mask.npy')
sea_cells = np.argwhere(sea_mask)
for ci, (lat_i, lon_i) in enumerate(sea_cells[:5]):
    t = threshold_smooth[:, lat_i, lon_i]
    c = climatology_smooth[:, lat_i, lon_i]
    print(f"Cell ({lat_i}, {lon_i}): threshold NaN count={np.isnan(t).sum()}, climatology NaN count={np.isnan(c).sum()}")
