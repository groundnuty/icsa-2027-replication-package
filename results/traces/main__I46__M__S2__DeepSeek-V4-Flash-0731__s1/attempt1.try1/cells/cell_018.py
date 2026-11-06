
import numpy as np

hot = np.load('/tmp/hot.npy')
sea_mask = np.load('/tmp/sea_mask.npy')

n_target, n_lat, n_lon = hot.shape

# Find per-cell MHW mask: 1 where cell is inside a per-cell MHW
# A per-cell MHW is a run of >=5 consecutive hot days
# MHWs separated by 1-2 non-hot days are joined

mhw_mask = np.zeros_like(hot, dtype=bool)

for li in range(n_lat):
    for loni in range(n_lon):
        if not sea_mask[li, loni]:
            continue
        
        # Get the hot sequence for this cell
        hot_seq = hot[:, li, loni]
        
        # Find runs of hot days
        runs = []
        i = 0
        while i < n_target:
            if hot_seq[i]:
                # Start of a run
                j = i
                while j < n_target and hot_seq[j]:
                    j += 1
                runs.append((i, j - 1))  # (start, end) inclusive
                i = j
            else:
                i += 1
        
        # Filter runs with length >= 5
        long_runs = [(s, e) for s, e in runs if e - s + 1 >= 5]
        
        # Join runs separated by 1-2 non-hot days
        if len(long_runs) == 0:
            continue
        
        joined_runs = [long_runs[0]]
        for s, e in long_runs[1:]:
            prev_s, prev_e = joined_runs[-1]
            gap = s - prev_e - 1  # number of non-hot days between
            if 1 <= gap <= 2:
                # Join
                joined_runs[-1] = (prev_s, e)
            else:
                joined_runs.append((s, e))
        
        # Mark MHW days
        for s, e in joined_runs:
            mhw_mask[s:e+1, li, loni] = True

print("Per-cell MHW mask shape:", mhw_mask.shape)
print("Cells in MHW at some point:", mhw_mask.any(axis=0).sum())
print("Total MHW cell-days:", mhw_mask.sum())

# Now identify regional events
# A day is active if at least one sea cell is in a per-cell MHW on that day
active = mhw_mask.any(axis=(1, 2))

print("Active days:", active.sum())
print("Active day indices:", np.where(active)[0])

# Regional events: maximal runs of consecutive active days
events = []
i = 0
while i < n_target:
    if active[i]:
        j = i
        while j < n_target and active[j]:
            j += 1
        events.append((i, j - 1))  # (start, end) inclusive
        i = j
    else:
        i += 1

print("Regional events:", len(events))
for s, e in events:
    print(f"  Event: target day {s} to {e} ({e - s + 1} days)")
