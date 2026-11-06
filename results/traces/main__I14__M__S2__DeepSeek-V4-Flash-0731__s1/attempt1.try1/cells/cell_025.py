
import numpy as np
import pandas as pd

lat_vals = np.load('/tmp/lat_vals.npy')
lon_vals = np.load('/tmp/lon_vals.npy')

lat_min, lat_max = 56.13, 57.33
lon_min, lon_max = 17.71, 18.91

print("Lat values in region:")
for i, lat in enumerate(lat_vals):
    if lat_min <= lat <= lat_max:
        if i < 5 or i > len(lat_vals) - 6:
            print(f"  idx {i}: {lat}")

# Find boundary indices
lat_idx = np.where((lat_vals >= lat_min) & (lat_vals <= lat_max))[0]
lon_idx = np.where((lon_vals >= lon_min) & (lon_vals <= lon_max))[0]
print(f"\nLat indices: {lat_idx[0]} to {lat_idx[-1]}, values: {lat_vals[lat_idx[0]]} to {lat_vals[lat_idx[-1]]}")
print(f"Lon indices: {lon_idx[0]} to {lon_idx[-1]}, values: {lon_vals[lon_idx[0]]} to {lon_vals[lon_idx[-1]]}")
print(f"Num lat: {len(lat_idx)}, num lon: {len(lon_idx)}")

# Check neighbors
if lat_idx[0] > 0:
    print(f"Lat below min: idx {lat_idx[0]-1}, value {lat_vals[lat_idx[0]-1]}")
if lat_idx[-1] < len(lat_vals) - 1:
    print(f"Lat above max: idx {lat_idx[-1]+1}, value {lat_vals[lat_idx[-1]+1]}")
if lon_idx[0] > 0:
    print(f"Lon below min: idx {lon_idx[0]-1}, value {lon_vals[lon_idx[0]-1]}")
if lon_idx[-1] < len(lon_vals) - 1:
    print(f"Lon above max: idx {lon_idx[-1]+1}, value {lon_vals[lon_idx[-1]+1]}")
