
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json
import os

# Load all intermediate data
threshold_smooth = np.load('/tmp/threshold_smooth.npy')
sea_mask = np.load('/tmp/sea_mask.npy')
target_sst = np.load('/tmp/target_sst.npy')
target_time = np.load('/tmp/target_time.npy')
hot = np.load('/tmp/hot.npy')
mhw_mask = np.load('/tmp/mhw_mask.npy')

# Verify the event detection
target_dates = [pd.Timestamp(t).to_pydatetime() for t in target_time]
active = mhw_mask.any(axis=(1, 2))
print("Active days (0-indexed):", np.where(active)[0])

# Print details about the event
n_time = len(target_dates)
i = 0
events = []
while i < n_time:
    if active[i]:
        start = i
        while i < n_time and active[i]:
            i += 1
        end = i - 1
        events.append((start, end))
    else:
        i += 1

for s, e in events:
    print(f"Event: {target_dates[s].strftime('%Y-%m-%d')} to {target_dates[e].strftime('%Y-%m-%d')}")
    print(f"  Start index: {s}, End index: {e}, Length: {e-s+1} days")
    print(f"  Cells in MHW on first day: {mhw_mask[s].sum()}")
    print(f"  Cells in MHW on last day: {mhw_mask[e].sum()}")
    # Check days before and after
    if s > 0:
        print(f"  Cells in MHW on day before ({target_dates[s-1].strftime('%Y-%m-%d')}): {mhw_mask[s-1].sum()}")
    if e < n_time - 1:
        print(f"  Cells in MHW on day after ({target_dates[e+1].strftime('%Y-%m-%d')}): {mhw_mask[e+1].sum()}")

# Verify that the regional event is a maximal run of active days
for i in range(n_time):
    if active[i]:
        # Check if there's a run of non-active days before this
        pass

# Check that the event ends when no cell is in an MHW
# (i.e., the day after the event has 0 MHW cells)
if events:
    s, e = events[0]
    if e + 1 < n_time:
        print(f"\nDay after event ({target_dates[e+1].strftime('%Y-%m-%d')}): {mhw_mask[e+1].sum()} MHW cells")
        print(f"Active day after event: {active[e+1]}")

print("\nVerification complete.")
