
import numpy as np
import pandas as pd

# Load data
time_int = np.load('/tmp/time_sub.npy')
time_sub = time_int.astype('datetime64[s]')
mhw_cell = np.load('/tmp/mhw_cell.npy')

target_start = np.datetime64('2022-06-01')
target_end = np.datetime64('2022-08-31')
target_mask = (time_sub >= target_start) & (time_sub <= target_end)
target_idx = np.where(target_mask)[0]
target_dates = [pd.Timestamp(time_sub[i]).strftime('%Y-%m-%d') for i in target_idx]

# Active day: at least one cell is in MHW
active = mhw_cell.any(axis=(1, 2))
print("Active days:", active.sum())
print("Active pattern:", active.astype(int))

# Find maximal runs of consecutive active days
runs = []
i = 0
while i < len(active):
    if active[i]:
        j = i
        while j < len(active) and active[j]:
            j += 1
        runs.append((i, j-1))
        i = j
    else:
        i += 1

print("Regional events (runs of active days):")
events = []
for s, e in runs:
    onset = target_dates[s]
    end = target_dates[e]
    events.append({"onset": onset, "end": end})
    print(f"  {onset} to {end}")

# Save events
import json
with open('/tmp/events.json', 'w') as f:
    json.dump(events, f)
