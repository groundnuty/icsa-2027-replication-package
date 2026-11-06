
import numpy as np
import datetime

# Load data
mhw_mask = np.load('mhw_mask.npy')
target_times_int = np.load('target_times.npy')
target_times = target_times_int.astype('datetime64[D]')
lat_vals = np.load('lat_vals.npy')
lon_vals = np.load('lon_vals.npy')

print("MHW mask shape:", mhw_mask.shape)
print("Target times:", target_times[0], "to", target_times[-1])

# Compute active days
# A day is active if at least one sea cell is inside a per-cell MHW on that day
active = np.any(mhw_mask > 0, axis=(1, 2))  # (92,)
print("Active days:", active.sum())

# Find maximal runs of consecutive active days
runs = []
i = 0
n = len(active)
while i < n:
    if active[i]:
        j = i
        while j < n and active[j]:
            j += 1
        runs.append((i, j-1))
        i = j
    else:
        i += 1

print("Regional events (target day indices):")
for s, e in runs:
    print(f"  Day {s} to {e}: {target_times[s]} to {target_times[e]}")
    print(f"    Active days: {e - s + 1}")

# Convert to dates
events = []
for s, e in runs:
    onset = np.datetime_as_string(target_times[s], unit='D')
    end = np.datetime_as_string(target_times[e], unit='D')
    events.append({"onset": onset, "end": end})

print("\nEvents:")
for ev in events:
    print(f"  {ev['onset']} to {ev['end']}")

# Print inactive days
inactive_days = np.where(~active)[0]
print("\nInactive days (target indices):", inactive_days)
if len(inactive_days) > 0:
    print("Inactive dates:", [np.datetime_as_string(target_times[i], unit='D') for i in inactive_days])
