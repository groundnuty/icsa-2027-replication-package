
import numpy as np

threshold = np.load('/tmp/threshold_smoothed.npy')
climatology = np.load('/tmp/climatology_smoothed.npy')
sea_cells = np.load('/tmp/sea_cells.npy')

# Check threshold and climatology values for sea cells in the target doy range (153-244)
tgt_doy_range = np.arange(153, 245)  # June 1 to Aug 31

thresh_subset = threshold[tgt_doy_range-1][:, sea_cells]
clim_subset = climatology[tgt_doy_range-1][:, sea_cells]

print(f"Threshold range (target doy, sea cells): {np.nanmin(thresh_subset):.2f} to {np.nanmax(thresh_subset):.2f} K")
print(f"Climatology range (target doy, sea cells): {np.nanmin(clim_subset):.2f} to {np.nanmax(clim_subset):.2f} K")
print(f"Threshold NaN: {np.isnan(thresh_subset).sum()}")
print(f"Climatology NaN: {np.isnan(clim_subset).sum()}")

# Check that thresholds are above climatology
diff = thresh_subset - clim_subset
print(f"Threshold - Climatology range: {np.nanmin(diff):.2f} to {np.nanmax(diff):.2f} K")
print(f"Negative differences: {(diff < 0).sum()}")

# Verify a specific cell's values
lat, lon = 52, 14
print(f"\nCell ({lat},{lon}) threshold values for target days:")
for i, doy in enumerate([153, 180, 200, 220, 244]):
    print(f"  doy={doy}: threshold={threshold[doy-1, lat, lon]:.2f} K, clim={climatology[doy-1, lat, lon]:.2f} K")
