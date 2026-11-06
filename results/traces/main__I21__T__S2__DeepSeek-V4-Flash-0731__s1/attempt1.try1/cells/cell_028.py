
import numpy as np
import xarray as xr
import pandas as pd

# Load intermediate results
mhw_mask = np.load('mhw_mask.npy')
target_data = xr.open_dataset('target_data.nc')
target_time = target_data.time.values
target_dates = [pd.Timestamp(t).to_pydatetime() for t in target_time]

# Active days: at least one cell in an MHW
active = np.any(mhw_mask > 0, axis=(1, 2))
print("Active days:")
for t in range(len(target_time)):
    status = "ACTIVE" if active[t] else "---"
    count = np.sum(mhw_mask[t, :, :] > 0)
    print(f"  {target_dates[t].strftime('%Y-%m-%d')}: {status}, cells_in_mhw={count}")

# Find regional events
events = []
i = 0
while i < len(target_time):
    if active[i]:
        start = i
        while i < len(target_time) and active[i]:
            i += 1
        end = i - 1
        events.append((start, end))
    else:
        i += 1

print(f"\nRegional events: {len(events)}")
for s, e in events:
    print(f"  {target_dates[s].strftime('%Y-%m-%d')} to {target_dates[e].strftime('%Y-%m-%d')} ({e-s+1} days)")
