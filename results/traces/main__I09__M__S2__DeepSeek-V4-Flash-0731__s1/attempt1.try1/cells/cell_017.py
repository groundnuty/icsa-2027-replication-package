
import numpy as np

thresholds_smoothed = np.load('/tmp/thresholds_smoothed.npy')
climatology_smoothed = np.load('/tmp/climatology_smoothed.npy')
sea_mask = np.load('/tmp/sea_mask.npy')

# Check NaN in smoothed thresholds for sea cells
nan_sea_thresh = np.isnan(thresholds_smoothed[:, sea_mask]).sum()
nan_sea_clim = np.isnan(climatology_smoothed[:, sea_mask]).sum()
print(f"NaN in smoothed thresholds for sea cells: {nan_sea_thresh}")
print(f"NaN in smoothed climatology for sea cells: {nan_sea_clim}")

# Check NaN for land cells
nan_land_thresh = np.isnan(thresholds_smoothed[:, ~sea_mask]).sum()
nan_land_clim = np.isnan(climatology_smoothed[:, ~sea_mask]).sum()
print(f"NaN in smoothed thresholds for land cells: {nan_land_thresh}")
print(f"NaN in smoothed climatology for land cells: {nan_land_clim}")

# Verify: for sea cells, check a specific DOY
print("Threshold[152] (DOY 153) for sea cells - NaN count:", np.isnan(thresholds_smoothed[152][sea_mask]).sum())
print("Threshold[243] (DOY 244) for sea cells - NaN count:", np.isnan(thresholds_smoothed[243][sea_mask]).sum())
