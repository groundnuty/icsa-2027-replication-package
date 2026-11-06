import h5py
import numpy as np

f = h5py.File('/work/sst_s2.nc', 'r')

# Get lat and lon for the region
lats = f['latitude'][217:277]  # indices 217-276
lons = f['longitude'][421:481]  # indices 421-480
print("Lats:", lats)
print("Lons:", lons)
print("Lat shape:", lats.shape)
print("Lon shape:", lons.shape)

# Get time values for the target period
time_raw = f['time'][9282:9374]
print("\nTime raw values:", time_raw[:3], "...", time_raw[-3:])

# Convert to datetime
from datetime import datetime, timedelta
epoch = datetime(1981, 1, 1)
target_times = [epoch + timedelta(seconds=int(t)) for t in time_raw]
print("Target times:", target_times[0], "to", target_times[-1])
print("Number of target times:", len(target_times))
