
import numpy as np

# Load intermediate results
threshold_smooth = np.load('/tmp/threshold_smooth.npy')
sea_cells = np.load('/tmp/sea_cells.npy')
target_sst = np.load('/tmp/target_sst.npy')
target_doy = np.load('/tmp/target_doy.npy')

target_doy_idx = target_doy - 1
thresh_for_target = threshold_smooth[target_doy_idx]

target_sst64 = target_sst.astype(np.float64)
hot = target_sst64 >= thresh_for_target

# Set land cells to not hot
hot[:, ~sea_cells] = False
print("Hot days (sea only):", hot.sum())

# Now detect per-cell MHWs
# For each cell, find runs of >=5 consecutive hot days
# Then join runs separated by 1-2 non-hot days

n_time, n_lat, n_lon = hot.shape

# Per-cell MHW mask: 1 if cell is in an MHW on that day
mhw_mask = np.zeros_like(hot, dtype=np.uint8)

for li in range(n_lat):
    for lo in range(n_lon):
        if not sea_cells[li, lo]:
            continue
        h = hot[:, li, lo]
        
        # Find hot runs
        # Runs of >=5 consecutive hot days
        # Then join runs separated by 1-2 non-hot days
        
        # First find all runs of hot days
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
                    # Join: extend the previous run to include the gap and this run
                    joined[-1][1] = r[1]
                else:
                    joined.append(list(r))
            
            # Mark MHW days
            for run in joined:
                mhw_mask[run[0]:run[1]+1, li, lo] = 1

print("MHW mask sum:", mhw_mask.sum())
print("Cells with any MHW day:", (mhw_mask.sum(axis=0) > 0).sum())

# Save mhw_mask
np.save('/tmp/mhw_mask.npy', mhw_mask)

# Also compute regional events
# A day is active if at least one cell is in an MHW on that day
active = mhw_mask.sum(axis=(1, 2)) > 0
print("Active days:", active.sum(), "of", n_time)

# Regional events: maximal runs of consecutive active days
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
    print("  Event:", e, "days:", e[1]-e[0]+1)
