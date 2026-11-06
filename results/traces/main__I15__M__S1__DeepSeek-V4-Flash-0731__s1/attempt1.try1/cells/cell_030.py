import numpy as np
from datetime import datetime, timedelta

# Load data
hot = np.load('/tmp/hot.npy')
in_mhw = np.load('/tmp/in_mhw.npy')
target_sst = np.load('/tmp/target_sst.npy')
sea_indices = np.load('/tmp/sea_indices.npy')

# Target dates
target_dates = []
d = datetime(2019, 6, 1)
while d <= datetime(2019, 8, 31):
    target_dates.append(d)
    d += timedelta(days=1)

# Find cells where joining happened (where there are long runs separated by <= 2 days)
# Look for cells where in_mhw differs from what you'd get from just long runs

# Check a few cells that have MHWs
cells_with_mhw = np.where(in_mhw.any(axis=1))[0]
print(f"Cells with MHWs: {len(cells_with_mhw)}")

# Find cells where joining was applied
# Check if there are cells where multiple long runs were joined
for c in cells_with_mhw[:10]:
    h = hot[c]
    runs = []
    i = 0
    while i < len(h):
        if h[i]:
            start = i
            while i < len(h) and h[i]:
                i += 1
            end = i - 1
            runs.append((start, end))
        else:
            i += 1
    
    long_runs = [(s, e) for (s, e) in runs if (e - s + 1) >= 5]
    
    if len(long_runs) > 1:
        # Check if any were joined
        joined = []
        current = long_runs[0]
        joined_flag = False
        for next_run in long_runs[1:]:
            gap = next_run[0] - current[1] - 1
            if gap <= 2:
                current = (current[0], next_run[1])
                joined_flag = True
            else:
                joined.append(current)
                current = next_run
        joined.append(current)
        
        if joined_flag:
            print(f"\nCell {c}: hot runs={runs}, long runs={long_runs}, joined={joined}")
            pattern = ''.join(['M' if in_mhw[c][t] else '.' for t in range(len(h))])
            print(f"  MHW pattern: {pattern}")
            
            # Print first few joined MHW days
            for s, e in joined:
                print(f"  Joined MHW: {target_dates[s].strftime('%Y-%m-%d')} to {target_dates[e].strftime('%Y-%m-%d')}")
