
import numpy as np
import pandas as pd

# Load data
mhw_cell = np.load('/tmp/mhw_cell.npy')
sea_mask = np.load('/tmp/sea_mask.npy')
time_int = np.load('/tmp/time_sub.npy')
time_sub = time_int.astype('datetime64[s]')

# Target period
target_start = np.datetime64('2022-06-01')
target_end = np.datetime64('2022-08-31')
target_mask = (time_sub >= target_start) & (time_sub <= target_end)
target_idx = np.where(target_mask)[0]

# Verify: check MHW pattern for a few cells
for (lat, lon) in [(30, 30), (0, 0), (59, 59)]:
    print(f"Cell ({lat},{lon}): sea={sea_mask[lat,lon]}")
    if sea_mask[lat, lon]:
        pattern = mhw_cell[:, lat, lon].astype(int)
        print(f"  MHW pattern: {''.join(str(x) for x in pattern)}")
        # Find MHW runs
        runs = []
        i = 0
        while i < len(pattern):
            if pattern[i]:
                j = i
                while j < len(pattern) and pattern[j]:
                    j += 1
                runs.append((i, j-1))
                i = j
            else:
                i += 1
        for s, e in runs:
            d1 = pd.Timestamp(time_sub[target_idx[s]]).strftime('%Y-%m-%d')
            d2 = pd.Timestamp(time_sub[target_idx[e]]).strftime('%Y-%m-%d')
            print(f"  MHW: {d1} to {d2} ({e-s+1} days)")

# Compute active days
active = mhw_cell.any(axis=(1, 2))
print(f"\nActive days: {active.sum()} out of {len(active)}")

# Find regional events
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

print("\nRegional events:")
for s, e in runs:
    d1 = pd.Timestamp(time_sub[target_idx[s]]).strftime('%Y-%m-%d')
    d2 = pd.Timestamp(time_sub[target_idx[e]]).strftime('%Y-%m-%d')
    print(f"  {d1} to {d2} ({e-s+1} days)")
