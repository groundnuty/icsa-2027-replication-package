
import numpy as np
import pandas as pd
from datetime import date

# Load data
mhw_mask = np.load('/work/mhw_mask.npy')  # (92, 60, 60)
sea_mask = np.load('/work/sea_mask.npy')

# Reload target dates
import xarray as xr
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
time_vals = ds.time.values
target_idx = np.where((time_vals >= np.datetime64('2021-06-01')) & (time_vals <= np.datetime64('2021-08-31')))[0]
target_time = time_vals[target_idx]
target_dates = [pd.Timestamp(t).date() for t in target_time]

# A day is active if at least one sea cell is in a per-cell MHW
active = mhw_mask.sum(axis=(1, 2)) > 0  # (92,)
print(f"Active days: {np.sum(active)}")
print(f"Active days indices: {np.where(active)[0]}")

# Find maximal runs of consecutive active days
active_indices = np.where(active)[0]
if len(active_indices) == 0:
    events = []
else:
    events = []
    start = active_indices[0]
    prev = active_indices[0]
    for d in active_indices[1:]:
        if d > prev + 1:
            events.append((start, prev))
            start = d
        prev = d
    events.append((start, prev))

# Convert to dates
event_list = []
for s, e in events:
    onset = target_dates[s].isoformat()
    end = target_dates[e].isoformat()
    event_list.append({"onset": onset, "end": end})
    print(f"Event: {onset} to {end} (days {s} to {e}, length {e-s+1})")

print(f"\nTotal events: {len(event_list)}")
