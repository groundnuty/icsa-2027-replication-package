
import numpy as np
import pandas as pd
from datetime import datetime
import pickle

# Load data
sst_data = np.load('/tmp/sst_data.npy')
times_int = np.load('/tmp/times.npy')
lat_vals = np.load('/tmp/lat_vals.npy')
lon_vals = np.load('/tmp/lon_vals.npy')

times = pd.to_datetime(times_int, unit='D')

# Target period: 2015-06-01 to 2015-08-31
target_start = np.datetime64('2015-06-01')
target_end = np.datetime64('2015-08-31')

times_np = times.values
target_mask = (times_np >= target_start) & (times_np <= target_end)
target_indices = np.where(target_mask)[0]
print("Target indices:", target_indices[0], "to", target_indices[-1], "count:", len(target_indices))
print("Target dates:", times[target_indices[0]].date(), "to", times[target_indices[-1]].date())

# Determine sea cells: cells with finite SST on every target day
target_sst = sst_data[target_indices, :, :]  # (92, 60, 60)
finite_all = np.all(np.isfinite(target_sst), axis=0)  # (60, 60)
n_sea = finite_all.sum()
print("Number of sea cells:", n_sea)
print("Sea cell count per row:", finite_all.sum(axis=1))
