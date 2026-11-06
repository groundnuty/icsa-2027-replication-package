
import numpy as np
from datetime import datetime, timedelta

# Load saved data
base_sst = np.load('/work/base_sst.npy')  # (4028, 60, 60)
target_sst = np.load('/work/target_sst.npy')  # (92, 60, 60)
region_lats = np.load('/work/region_lats.npy')
region_lons = np.load('/work/region_lons.npy')
base_times = np.load('/work/base_times.npy')
target_times = np.load('/work/target_times.npy')

print("Base times:", base_times[0], "to", base_times[-1])
print("Target times:", target_times[0], "to", target_times[-1])
print("Base shape:", base_sst.shape)
print("Target shape:", target_sst.shape)
