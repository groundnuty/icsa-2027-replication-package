
import numpy as np
import xarray as xr
from datetime import date, timedelta
import pandas as pd
from collections import defaultdict

# Reload and recompute (since sandbox doesn't persist between calls unless saved)
# Let me save intermediate results first
import pickle

# Actually, let me just do everything in one comprehensive script
# Let me check if I can save the computed arrays
np.save('thresholds_raw.npy', thresholds)
np.save('climatology_raw.npy', climatology)
print("Saved raw thresholds and climatology")

# Set day 60
thresholds[60] = (thresholds[59] + thresholds[61]) / 2.0
climatology[60] = (climatology[59] + climatology[61]) / 2.0
print("Day 60 set")

# Smoothing: unweighted centred 31-day moving mean that wraps around the year
# Day d averages days d-15 ... d+15, counted modulo 366
# Note: using indices 1-366 (since we have 367 elements with index 0 unused)

def smooth_wrap(arr, window=31, days_per_year=366):
    """Smooth a 367-length array (indices 0-366, with index 0 unused) using a 31-day moving average wrapping around."""
    # Extract indices 1-366
    data = arr[1:367].copy()  # shape (366, n_lat, n_lon)
    half = window // 2  # 15
    n = days_per_year  # 366
    result = np.zeros_like(data, dtype=np.float64)
    
    for d in range(n):
        # indices d-half to d+half, modulo n
        total = np.zeros(data.shape[1:], dtype=np.float64)
        count = np.zeros(data.shape[1:], dtype=np.float64)
        for k in range(d - half, d + half + 1):
            idx = k % n
            vals = data[idx]
            mask = ~np.isnan(vals)
            total[mask] += vals[mask]
            count[mask] += 1
        result[d] = total / np.maximum(count, 1)
    
    # Put back into 367-length array
    smoothed = np.zeros_like(arr, dtype=np.float64)
    smoothed[1:367] = result
    return smoothed

thresholds_smooth = smooth_wrap(thresholds)
climatology_smooth = smooth_wrap(climatology)

print("Smoothed thresholds shape:", thresholds_smooth.shape)
print("Sample smoothed threshold DOY 1, cell (0,0):", thresholds_smooth[1, 0, 0])
print("Sample smoothed climatology DOY 1, cell (0,0):", climatology_smooth[1, 0, 0])

np.save('thresholds_smooth.npy', thresholds_smooth)
np.save('climatology_smooth.npy', climatology_smooth)
print("Saved smoothed arrays")
