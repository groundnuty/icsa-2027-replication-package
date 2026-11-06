
import numpy as np
import xarray as xr
import json
import datetime
import pandas as pd

# Load the output files
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
mhw = ds.mhw.values
print(f"mhw shape: {mhw.shape}")
print(f"mhw dtype: {mhw.dtype}")
print(f"mhw sum: {mhw.sum()}")
print(f"mhw values: {np.unique(mhw)}")

# Check active days
active = mhw.any(axis=(1,2))
print(f"\nActive day indices: {np.where(active)[0]}")
time_vals = ds.time.values
for t in np.where(active)[0]:
    print(f"  Day {t}: {pd.Timestamp(time_vals[t]).strftime('%Y-%m-%d')} - {mhw[t].sum()} cells in MHW")

# Verify regional events from mask
n = len(time_vals)
events_from_mask = []
start = None
for t in range(n):
    if active[t]:
        if start is None:
            start = t
    else:
        if start is not None:
            events_from_mask.append((start, t-1))
            start = None
if start is not None:
    events_from_mask.append((start, n-1))

print(f"\nEvents from mask:")
for s, e in events_from_mask:
    onset = pd.Timestamp(time_vals[s]).strftime('%Y-%m-%d')
    end = pd.Timestamp(time_vals[e]).strftime('%Y-%m-%d')
    print(f"  {onset} to {end} ({e-s+1} days)")

# Read report
with open('output/report.json', 'r') as f:
    report = json.load(f)
print(f"\nReport events:")
for ev in report['events']:
    print(f"  {ev['onset']} to {ev['end']}")

# Check that the mask values match the report events
print(f"\nMask/report consistency check:")
for ev in report['events']:
    onset_date = datetime.date.fromisoformat(ev['onset'])
    end_date = datetime.date.fromisoformat(ev['end'])
    
    # Find indices
    onset_idx = None
    end_idx = None
    for t in range(n):
        d = pd.Timestamp(time_vals[t]).to_pydatetime().date()
        if d == onset_date:
            onset_idx = t
        if d == end_date:
            end_idx = t
    
    if onset_idx is not None and end_idx is not None:
        # Check all days in between are active
        all_active = active[onset_idx:end_idx+1].all()
        print(f"  {ev['onset']} to {ev['end']}: all active = {all_active}")
        # Check that the days just before onset and after end are NOT active
        before_active = active[onset_idx-1] if onset_idx > 0 else False
        after_active = active[end_idx+1] if end_idx < n-1 else False
        print(f"    Before onset active: {before_active}, After end active: {after_active}")
