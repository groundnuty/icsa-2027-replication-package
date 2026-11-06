
import numpy as np
import pandas as pd

# Load data
mhw_mask = np.load('/work/mhw_mask.npy')
target_time = np.load('/work/target_time.npy', allow_pickle=True)
tt = pd.to_datetime(target_time)

# Compute active days
active = mhw_mask.sum(axis=(1, 2)) > 0

# Verify that days outside the active period have 0 MHW cells
print("Active days:")
for i in range(92):
    if active[i]:
        n_cells = mhw_mask[i].sum()
        print(f"  Day {i} ({tt[i].strftime('%Y-%m-%d')}): {n_cells} cells in MHW")

# Verify boundaries
print("\nDay 64 (2004-08-04): cells in MHW =", mhw_mask[64].sum())
print("Day 65 (2004-08-05): cells in MHW =", mhw_mask[65].sum())
print("Day 75 (2004-08-15): cells in MHW =", mhw_mask[75].sum())
print("Day 76 (2004-08-16): cells in MHW =", mhw_mask[76].sum())

# Verify the event detection
events = []
active_indices = np.where(active)[0]
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
for s, e in events:
    print(f"  Onset: {tt[s].strftime('%Y-%m-%d')}, End: {tt[e].strftime('%Y-%m-%d')}, Duration: {e-s+1} days")
