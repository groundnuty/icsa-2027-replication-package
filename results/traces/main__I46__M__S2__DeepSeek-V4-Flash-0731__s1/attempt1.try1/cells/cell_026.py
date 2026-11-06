
import xarray as xr
import numpy as np

# Load a sample sea cell and check its threshold/climatology
threshold_smooth = np.load('/tmp/threshold_smooth.npy')
climatology_smooth = np.load('/tmp/climatology_smooth.npy')

# Pick a sea cell (e.g., cell at lat index 30, lon index 30)
li, loni = 30, 30
sea_mask = np.load('/tmp/sea_mask.npy')
print(f"Cell ({li}, {loni}) is sea:", sea_mask[li, loni])

# Check threshold and climatology for days around June
for doy in [153, 160, 170, 180, 190, 200, 210, 220, 230, 240, 244]:
    print(f"Day {doy}: threshold={threshold_smooth[doy-1, li, loni]:.4f}, climatology={climatology_smooth[doy-1, li, loni]:.4f}")

# Check the raw threshold before smoothing
threshold_raw = np.load('/tmp/threshold_raw.npy')
climatology_raw = np.load('/tmp/climatology_raw.npy')
print("\nRaw (before smoothing):")
for doy in [153, 160, 170, 180, 190, 200, 210, 220, 230, 240, 244]:
    print(f"Day {doy}: threshold={threshold_raw[doy-1, li, loni]:.4f}, climatology={climatology_raw[doy-1, li, loni]:.4f}")

# Check day 60 handling
print("\nDay 59/60/61 raw:")
for doy in [59, 60, 61]:
    print(f"Day {doy}: threshold={threshold_raw[doy-1, li, loni]:.4f}, climatology={climatology_raw[doy-1, li, loni]:.4f}")
