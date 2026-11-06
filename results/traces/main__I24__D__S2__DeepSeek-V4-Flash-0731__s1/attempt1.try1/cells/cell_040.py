
import numpy as np

# Load raw threshold
threshold_raw = np.load('/work/threshold_raw.npy')
threshold_smooth = np.load('/work/threshold_smooth.npy')

# For doy 153 (index 152), smooth over indices 137-167 (153-15=138 to 153+15=168, i.e., indices 137-167)
# Wait, let me be careful with the mapping.
# doy d corresponds to index d-1
# Smooth for doy 153: average raw values for doy 138-168 (indices 137-167)
# Actually, day d averages days d-15 to d+15, counted modulo 366.
# So for day 153: days 138 to 168, indices 137 to 167.

indices = [(152 + offset) % 366 for offset in range(-15, 16)]
print("Indices for smoothing doy 153:", indices[:5], "...", indices[-5:])

# Check: index 152-15 = 137 (doy 138), index 152+15 = 167 (doy 168)
print("Index 137 -> doy", 137+1)
print("Index 167 -> doy", 167+1)

# Manual smoothed threshold
sea_cells = np.all(np.isfinite(np.load('/work/target_sst.npy')), axis=0)
lat_i, lon_i = 0, 9
manual_smooth = np.mean(threshold_raw[indices, lat_i, lon_i])
print(f"\nManual smoothed threshold at doy 153: {manual_smooth:.6f}")
print(f"Numpy smoothed threshold at doy 153: {threshold_smooth[152, lat_i, lon_i]:.6f}")
print(f"Match: {abs(manual_smooth - threshold_smooth[152, lat_i, lon_i]) < 1e-10}")

# Also verify day 60 value
# Day 60 (index 59) should be mean of days 59 and 61 (indices 58 and 60)
print(f"\nRaw threshold doy 59: {threshold_raw[58, lat_i, lon_i]:.6f}")
print(f"Raw threshold doy 60: {threshold_raw[59, lat_i, lon_i]:.6f}")
print(f"Raw threshold doy 61: {threshold_raw[60, lat_i, lon_i]:.6f}")
print(f"Mean of days 59 and 61: {(threshold_raw[58, lat_i, lon_i] + threshold_raw[60, lat_i, lon_i])/2:.6f}")
