
import numpy as np
import pandas as pd
import xarray as xr

# Load the computed mhw mask
ds_out = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
mhw = ds_out['mhw'].values

n_target = mhw.shape[0]
n_lat, n_lon = mhw.shape[1], mhw.shape[2]

# Print the number of cells in MHW on each day
print("Day-by-day active cells:")
for t in range(n_target):
    active_cells = mhw[t].sum()
    date_str = pd.Timestamp(ds_out.time.values[t]).strftime('%Y-%m-%d')
    if active_cells > 0:
        print(f"  {date_str}: {active_cells} cells in MHW")

# Find regional event boundaries
active = mhw.sum(axis=(1,2)) > 0
print(f"\nActive days: {active.sum()}")

# Identify events
events = []
in_event = False
for t in range(n_target):
    if active[t]:
        if not in_event:
            event_start = t
            in_event = True
    else:
        if in_event:
            events.append((event_start, t-1))
            in_event = False
if in_event:
    events.append((event_start, n_target-1))

print("Regional events:")
for s, e in events:
    onset = pd.Timestamp(ds_out.time.values[s]).strftime('%Y-%m-%d')
    end = pd.Timestamp(ds_out.time.values[e]).strftime('%Y-%m-%d')
    print(f"  {onset} to {end}")
