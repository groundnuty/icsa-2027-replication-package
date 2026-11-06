
import numpy as np
import pandas as pd

# Load
mhw_mask = np.load('/work/mhw_mask.npy')  # (92, 60, 60) uint8
target_time = np.load('/work/target_time.npy', allow_pickle=True)
tt = pd.to_datetime(target_time)

# For each target day, check if any sea cell is in a per-cell MHW
active = mhw_mask.sum(axis=(1, 2)) > 0  # (92,) boolean
print("Active days:", active.sum(), "out of", len(active))

# Print active days
active_indices = np.where(active)[0]
print("Active day indices:", active_indices)
for idx in active_indices:
    print(f"  Day {idx}: {tt[idx].strftime('%Y-%m-%d')}, cells in MHW: {mhw_mask[idx].sum()}")

# Find maximal runs of consecutive active days
events = []
if len(active_indices) > 0:
    start = active_indices[0]
    prev = start
    for idx in active_indices[1:]:
        if idx == prev + 1:
            prev = idx
        else:
            events.append((start, prev))
            start = idx
            prev = idx
    events.append((start, prev))

print("\nRegional events:")
regional_events = []
for s, e in events:
    onset = tt[s].strftime('%Y-%m-%d')
    end = tt[e].strftime('%Y-%m-%d')
    print(f"  Onset: {onset}, End: {end}, Duration: {e-s+1} days")
    regional_events.append({"onset": onset, "end": end})

print("\nNumber of regional events:", len(regional_events))
