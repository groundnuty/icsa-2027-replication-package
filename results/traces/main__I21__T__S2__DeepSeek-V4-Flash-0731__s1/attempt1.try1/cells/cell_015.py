
import numpy as np
import pandas as pd
from datetime import datetime

# Load MHW mask
mhw_mask = np.load('mhw_mask.npy')

# Load target data
import xarray as xr
target_data = xr.open_dataset('target_data.nc')
target_time = target_data.time.values
target_dates = [pd.Timestamp(t).to_pydatetime() for t in target_time]
n_time = len(target_time)

# A day is active if at least one sea cell is inside a per-cell MHW on that day
active = np.any(mhw_mask > 0, axis=(1, 2))

print("Active days:")
for t in range(n_time):
    if active[t]:
        print(f"  {target_dates[t].strftime('%Y-%m-%d')}")

# Find regional events (maximal runs of consecutive active days)
events = []
i = 0
while i < n_time:
    if active[i]:
        start = i
        while i < n_time and active[i]:
            i += 1
        end = i - 1
        events.append((start, end))
    else:
        i += 1

print(f"\nRegional events: {len(events)}")
for s, e in events:
    print(f"  {target_dates[s].strftime('%Y-%m-%d')} to {target_dates[e].strftime('%Y-%m-%d')} ({e-s+1} days)")
