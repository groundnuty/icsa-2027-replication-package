
import numpy as np
import pandas as pd
from datetime import date, timedelta

# Load data
smooth_thresholds = np.load('/work/smooth_thresholds.npy')
smooth_climatology = np.load('/work/smooth_climatology.npy')
thresholds_raw = np.load('/work/thresholds.npy')
climatology_raw = np.load('/work/climatology.npy')

# Check a sea cell, say (30, 30)
i, j = 30, 30

print(f"Cell ({i},{j}):")
print(f"  Raw threshold doy 153: {thresholds_raw[152, i, j]}")
print(f"  Raw climatology doy 153: {climatology_raw[152, i, j]}")
print(f"  Smoothed threshold doy 153: {smooth_thresholds[152, i, j]}")
print(f"  Smoothed climatology doy 153: {smooth_climatology[152, i, j]}")

# Check day 60 handling
print(f"  Raw threshold doy 59: {thresholds_raw[58, i, j]}")
print(f"  Raw threshold doy 60: {thresholds_raw[59, i, j]}")
print(f"  Raw threshold doy 61: {thresholds_raw[60, i, j]}")
print(f"  Expected day 60: {(thresholds_raw[58, i, j] + thresholds_raw[60, i, j]) / 2}")

# Verify the smoothing is correct for this cell
# Manually compute the smoothed value for doy 153
raw = thresholds_raw[:, i, j]
doy_153_smoothed = np.mean([raw[(152 - 15 + k) % 366] for k in range(31)])
print(f"  Manual smoothing doy 153: {doy_153_smoothed}")
print(f"  Code smoothing doy 153: {smooth_thresholds[152, i, j]}")
