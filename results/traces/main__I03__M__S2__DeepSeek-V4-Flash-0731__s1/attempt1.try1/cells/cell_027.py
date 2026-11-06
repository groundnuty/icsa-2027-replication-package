
import numpy as np
from datetime import datetime

# Load corrected intermediate results
threshold_smooth = np.load('/tmp/threshold_smooth_correct.npy')
sea_cells = np.load('/tmp/sea_cells.npy')
target_sst = np.load('/tmp/target_sst.npy')
target_doy = np.load('/tmp/target_doy.npy')

print("Target doy:", target_doy[0], "to", target_doy[-1])
print("Target SST shape:", target_sst.shape)

# Convert doy (1-366) to 0-based index (0-365)
target_doy_idx = target_doy - 1

# Get thresholds for each target day
thresh_for_target = threshold_smooth[target_doy_idx]  # (92, 60, 60)
print("Threshold shape for target:", thresh_for_target.shape)

# Hot days: SST >= threshold
target_sst64 = target_sst.astype(np.float64)
hot = target_sst64 >= thresh_for_target
print("Hot days count:", hot.sum())

# Set land cells to not hot
hot[:, ~sea_cells] = False
print("Hot days (sea only):", hot.sum())

# Detect per-cell MHWs
n_time, n_lat, n_lon = hot.shape
mhw_mask = np.zeros_like(hot, dtype=np.uint8)

for li in range(n_lat):
    for lo in range(n_lon):
        if not sea_cells[li, lo]:
            continue
        h = hot[:, li, lo]
        
        # Find runs of hot days
        runs = []
        in_run = False
        start = 0
        for i in range(n_time):
            if h[i] and not in_run:
                start = i
                in_run = True
            elif not h[i] and in_run:
                runs.append((start, i-1))
                in_run = False
        if in_run:
            runs.append((start, n_time-1))
        
        # Filter runs with >=5 days
        long_runs = [r for r in runs if r[1] - r[0] + 1 >= 5]
        
        # Join runs separated by 1-2 non-hot days
        if long_runs:
            joined = [list(long_runs[0])]
            for r in long_runs[1:]:
                gap = r[0] - joined[-1][1] - 1
                if gap >= 1 and gap <= 2:
                    joined[-1][1] = r[1]
                else:
                    joined.append(list(r))
            
            for run in joined:
                mhw_mask[run[0]:run[1]+1, li, lo] = 1

print("MHW mask sum:", mhw_mask.sum())
print("Cells with any MHW day:", (mhw_mask.sum(axis=0) > 0).sum())

# Regional events
active = mhw_mask.sum(axis=(1, 2)) > 0
print("Active days:", active.sum(), "of", n_time)

events = []
in_event = False
start = 0
for i in range(n_time):
    if active[i] and not in_event:
        start = i
        in_event = True
    elif not active[i] and in_event:
        events.append((start, i-1))
        in_event = False
if in_event:
    events.append((start, n_time-1))

print("Regional events:", len(events))
for e in events:
    print(f"  Event: indices {e[0]}-{e[1]}, days={e[1]-e[0]+1}")

# Save results
np.save('/tmp/mhw_mask_correct.npy', mhw_mask)
np.save('/tmp/active_correct.npy', active)
