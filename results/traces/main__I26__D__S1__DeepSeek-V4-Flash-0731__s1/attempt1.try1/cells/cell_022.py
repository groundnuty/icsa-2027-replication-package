import h5py
import numpy as np

f = h5py.File('/work/sst_s2.nc', 'r')

lats = f['latitude'][:]
lons = f['longitude'][:]
print("Lat dtype:", lats.dtype, "range:", lats.min(), lats.max())
print("Lon dtype:", lons.dtype, "range:", lons.min(), lons.max())

# Find indices for region: lat 57.83-59.03, lon 17.41-18.61
lat_mask = (lats >= 57.83) & (lats <= 59.03)
lon_mask = (lons >= 17.41) & (lons <= 18.61)
lat_idx = np.where(lat_mask)[0]
lon_idx = np.where(lon_mask)[0]
print(f"Lat indices: {lat_idx[0]} to {lat_idx[-1]}, count={len(lat_idx)}")
print(f"Lon indices: {lon_idx[0]} to {lon_idx[-1]}, count={len(lon_idx)}")
print(f"Selected lats: {lats[lat_idx[0]]} to {lats[lat_idx[-1]]}")
print(f"Selected lons: {lons[lon_idx[0]]} to {lons[lon_idx[-1]]}")
print(f"Lat step: {lats[1] - lats[0]}")
print(f"Lon step: {lons[1] - lons[0]}")
