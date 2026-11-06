
import h5py
import numpy as np

data_dir = '/data/icsa2027_data_20261101T090944Z/s1z'

# Get lat/lon coordinates from a sample file
with h5py.File(f'{data_dir}/sst_20140601.nc', 'r') as f:
    lat_all = f['latitude'][:]
    lon_all = f['longitude'][:]

# Get the region coordinates
lat_region = lat_all[278:338]
lon_region = lon_all[613:673]
print(f"Lat region: {lat_region[0]} to {lat_region[-1]}, shape: {lat_region.shape}")
print(f"Lon region: {lon_region[0]} to {lon_region[-1]}, shape: {lon_region.shape}")

# Save for later
np.save('output/lat_region.npy', lat_region)
np.save('output/lon_region.npy', lon_region)
print("Saved region coordinates")
