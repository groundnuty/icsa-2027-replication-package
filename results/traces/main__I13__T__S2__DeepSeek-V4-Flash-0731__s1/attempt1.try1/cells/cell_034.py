
import numpy as np
import datetime

# Load data
sst_target = np.load('sst_target.npy')
target_times_int = np.load('target_times.npy')
target_times = target_times_int.astype('datetime64[D]')
hot = np.load('hot.npy')
mhw_mask = np.load('mhw_mask.npy')

# Check cell (0, 0)
print("=== Cell (0, 0) ===")
print("Hot pattern:")
for t in range(92):
    date_str = np.datetime_as_string(target_times[t], unit='D')
    h = hot[t, 0, 0]
    m = mhw_mask[t, 0, 0]
    if h or m:
        print(f"  Day {t:3d} ({date_str}): hot={h}, mhw={m}")

print("\n=== Cell (0, 1) ===")
print("Hot pattern:")
for t in range(92):
    date_str = np.datetime_as_string(target_times[t], unit='D')
    h = hot[t, 0, 1]
    m = mhw_mask[t, 0, 1]
    if h or m:
        print(f"  Day {t:3d} ({date_str}): hot={h}, mhw={m}")
