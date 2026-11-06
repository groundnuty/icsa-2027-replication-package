import numpy as np

threshold_smooth = np.load('/tmp/work/threshold_smooth.npy')
climatology_smooth = np.load('/tmp/work/climatology_smooth.npy')

# Find a sea cell and check values
sea_cells = np.isfinite(threshold_smooth[0])
print(f"Sea cells on day 1: {sea_cells.sum()}")

idx = np.argwhere(sea_cells)[0]
print(f"First sea cell indices: {idx}")
print(f"  Threshold day 153: {threshold_smooth[152, idx[0], idx[1]]}")
print(f"  Climatology day 153: {climatology_smooth[152, idx[0], idx[1]]}")

# Check thresholds around day 153 (June 1) for a few sea cells
print("\nSome sea cell threshold/climatology values around June-Aug:")
for di in range(152, 245, 30):
    d = di + 1  # day of year
    print(f"  Day {d}: threshold={threshold_smooth[di, idx[0], idx[1]]:.3f}, clim={climatology_smooth[di, idx[0], idx[1]]:.3f}")

# Verify threshold > climatology (should generally be true for warm days)
print(f"\nCheck threshold > climatology for first sea cell (all days):")
valid = np.isfinite(threshold_smooth[:, idx[0], idx[1]])
print(f"  All valid days have threshold > climatology: {np.all(threshold_smooth[valid, idx[0], idx[1]] > climatology_smooth[valid, idx[0], idx[1]])}")
