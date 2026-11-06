
import numpy as np
import datetime

def day_of_year(date):
    y, m, d = date.year, date.month, date.day
    months = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    is_leap = (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0)
    doy = sum(months[:m-1]) + d
    if m > 2 and is_leap:
        doy += 1
    if not is_leap and m > 2:
        doy += 1
    return doy

# Load cached data
cached = np.load('cache/target_data.npz')
target_dates = [datetime.date.fromordinal(int(d)) for d in np.load('cache/target_dates.npy')]
target_sst = {}
for d in target_dates:
    target_sst[d] = cached[d.strftime('%Y%m%d')]

# Load smoothed threshold and climatology
threshold_sm = np.load('cache/threshold_smoothed.npy')
clim_sm = np.load('cache/clim_smoothed.npy')

n_target = len(target_dates)
n_lat, n_lon = 60, 60

# Build target SST array: (n_target, n_lat, n_lon)
target_array = np.array([target_sst[d] for d in target_dates], dtype=np.float64)
print(f'Target array shape: {target_array.shape}')

# Determine sea cells: cells with finite SST on every target day
sea_cells = np.all(np.isfinite(target_array), axis=0)
print(f'Sea cells: {sea_cells.sum()} out of {n_lat*n_lon}')

# Get doy for each target date
target_doy = np.array([day_of_year(d) for d in target_dates])
print(f'Target doy range: {target_doy.min()} to {target_doy.max()}')

# Build per-cell hot day mask
# hot[i, j, t] = True if target_array[t,i,j] >= threshold_sm[target_doy[t]-1, i, j]
hot = np.zeros((n_lat, n_lon, n_target), dtype=bool)

for t in range(n_target):
    doy = target_doy[t]
    for i in range(n_lat):
        for j in range(n_lon):
            if sea_cells[i, j] and not np.isnan(threshold_sm[doy-1, i, j]):
                hot[i, j, t] = target_array[t, i, j] >= threshold_sm[doy-1, i, j]

print(f'Hot cells per day: {hot.sum(axis=(0,1))}')

# Find per-cell MHWs
# A run of >=5 consecutive hot days
# MHWs separated by 1-2 non-hot days are joined
# We need to apply this per cell

# Let me do this more efficiently using vectorized operations

# For each cell, find runs of hot days in the target period
# Then apply the gap-joining rule

# First, build the per-cell MHW membership array: mhw_mask[i,j,t]
mhw_mask = np.zeros((n_lat, n_lon, n_target), dtype=bool)

for i in range(n_lat):
    for j in range(n_lon):
        if not sea_cells[i, j]:
            continue
        
        h = hot[i, j]  # (n_target,) boolean
        
        # Find runs of hot days
        # First, mark each day as hot or not
        # Then find maximal runs of hot days
        # A per-cell MHW is a run of >=5 consecutive hot days
        # MHWs separated by 1-2 non-hot days are joined
        
        # Approach: iteratively join runs separated by 1-2 gaps
        # Step 1: find all runs of hot days
        runs = []
        t = 0
        while t < n_target:
            if h[t]:
                start = t
                while t < n_target and h[t]:
                    t += 1
                runs.append([start, t-1])
            else:
                t += 1
        
        # Step 2: join runs separated by 1-2 non-hot days
        # Repeatedly check if consecutive runs can be joined
        changed = True
        while changed and len(runs) > 1:
            changed = False
            new_runs = []
            for k in range(len(runs)):
                if k < len(runs) - 1:
                    gap = runs[k+1][0] - runs[k][1] - 1
                    if gap <= 2 and gap >= 1:
                        # Join runs k and k+1
                        new_runs.append([runs[k][0], runs[k+1][1]])
                        # Skip k+1
                        if k + 1 < len(runs) - 1:
                            # Need to handle properly
                            pass
                        changed = True
                        # Mark that we need to reprocess
                        break
                new_runs.append(runs[k])
            
            if changed:
                runs = new_runs
        
        # Actually, the above loop is incorrect. Let me do it more carefully.
        # I need to iterate: repeatedly merge consecutive runs separated by <=2 non-hot days
        # until no more merging is possible
        
        # Let me redo this properly
        runs = []
        t = 0
        while t < n_target:
            if h[t]:
                start = t
                while t < n_target and h[t]:
                    t += 1
                runs.append([start, t-1])
            else:
                t += 1
        
        if not runs:
            continue
        
        # Merge runs
        merged = [runs[0]]
        for k in range(1, len(runs)):
            gap = runs[k][0] - merged[-1][1] - 1
            if 1 <= gap <= 2:
                merged[-1][1] = runs[k][1]
            else:
                merged.append(runs[k])
        
        # After merging, check if any merged run has >= 5 hot days
        # Wait - after joining, we need to check if the joined run has at least 5 hot days total?
        # Re-reading the spec:
        # "a per-cell MHW is a run of at least 5 consecutive hot days"
        # "per-cell MHWs separated by 1 or 2 non-hot days are joined into one"
        
        # So the process is:
        # 1. Find all runs of consecutive hot days (>=5)
        # 2. Join runs separated by 1-2 non-hot days
        # But we should find runs first, then only join runs that are each MHWs (>=5 days)?
        # Or join runs first and then check if the combined run has >=5 days?
        
        # Let me re-read: "a per-cell MHW is a run of at least 5 consecutive hot days"
        # "per-cell MHWs separated by 1 or 2 non-hot days are joined into one, and the gap days belong to it"
        
        # So we first identify MHWs (runs >= 5 hot days), then join those that are separated by 1-2 non-hot days.
        # Runs that are < 5 days are NOT MHWs and should not be joined.
        
        # So the algorithm is:
        # 1. Find all runs of consecutive hot days
        # 2. Identify which runs have >= 5 days (these are MHWs)
        # 3. Join MHWs separated by 1-2 non-hot days
        
        # Let me implement this properly:
        
        # Step 1: Find all runs of hot days
        runs = []
        t = 0
        while t < n_target:
            if h[t]:
                start = t
                while t < n_target and h[t]:
                    t += 1
                runs.append([start, t-1])
            else:
                t += 1
        
        # Step 2: Keep only runs with >= 5 days (these are MHWs)
        mhw_runs = [r for r in runs if r[1] - r[0] + 1 >= 5]
        
        # Step 3: Join MHWs separated by 1-2 non-hot days
        if mhw_runs:
            joined = [mhw_runs[0]]
            for k in range(1, len(mhw_runs)):
                gap = mhw_runs[k][0] - joined[-1][1] - 1
                if 1 <= gap <= 2:
                    joined[-1][1] = mhw_runs[k][1]
                else:
                    joined.append(mhw_runs[k])
            
            # Step 4: Mark all days in joined MHWs
            for r in joined:
                mhw_mask[i, j, r[0]:r[1]+1] = True

print(f'Per-cell MHW mask: {mhw_mask.sum()} cells-day')

# Regional events
# A day is active if at least one sea cell is inside a per-cell MHW on that day
active = np.any(mhw_mask, axis=(0, 1))
print(f'Active days: {active.sum()}')

# Regional MHW events = maximal runs of consecutive active days
events = []
t = 0
while t < n_target:
    if active[t]:
        start = t
        while t < n_target and active[t]:
            t += 1
        events.append([target_dates[start], target_dates[t-1]])
    else:
        t += 1

print(f'Number of regional events: {len(events)}')
for ev in events:
    print(f'  {ev[0]} to {ev[1]}')
