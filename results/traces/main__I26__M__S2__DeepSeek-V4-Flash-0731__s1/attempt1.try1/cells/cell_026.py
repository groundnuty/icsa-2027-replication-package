
import numpy as np
import pandas as pd
from datetime import date, timedelta
from collections import defaultdict
import time

def day_of_year_custom(dt):
    month = dt.month
    day = dt.day
    cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[month - 1] + day

# Load intermediate results
threshold = np.load('/tmp/threshold_smoothed.npy')
climatology = np.load('/tmp/climatology_smoothed.npy')
sea_cells = np.load('/tmp/sea_cells.npy')
tgt_data = np.load('/tmp/tgt_data.npy')
tgt_doy = np.load('/tmp/tgt_doy.npy')

n_tgt = len(tgt_data)
n_lat, n_lon = 60, 60

# Compute hot days
hot = np.zeros((n_tgt, n_lat, n_lon), dtype=bool)
for t in range(n_tgt):
    doy = tgt_doy[t]
    hot[t] = tgt_data[t] >= threshold[doy-1]

print(f"Hot days computed. Total hot cell-days: {hot.sum()}")

# Per-cell MHW detection with interpretation B:
# 1. Find runs of consecutive hot days
# 2. A run with >= 5 hot days is a per-cell MHW
# 3. Per-cell MHWs separated by 1-2 non-hot days are joined

per_cell_mhw_B = np.zeros((n_tgt, n_lat, n_lon), dtype=bool)

for lat in range(n_lat):
    for lon in range(n_lon):
        if not sea_cells[lat, lon]:
            continue
        
        hot_series = hot[:, lat, lon]
        
        # Find runs of consecutive hot days
        runs = []
        in_run = False
        run_start = 0
        for t in range(n_tgt):
            if hot_series[t]:
                if not in_run:
                    run_start = t
                    in_run = True
            else:
                if in_run:
                    runs.append((run_start, t-1))
                    in_run = False
        if in_run:
            runs.append((run_start, n_tgt-1))
        
        # Identify MHWs: runs with >= 5 hot days
        mhws = [(s, e) for (s, e) in runs if (e - s + 1) >= 5]
        
        # Join MHWs separated by 1-2 non-hot days
        if len(mhws) > 1:
            joined_mhws = []
            current = list(mhws[0])
            for i in range(1, len(mhws)):
                gap = mhws[i][0] - current[1] - 1
                if gap <= 2:
                    current[1] = mhws[i][1]
                else:
                    joined_mhws.append(tuple(current))
                    current = list(mhws[i])
            joined_mhws.append(tuple(current))
            mhws = joined_mhws
        
        # Mark MHW days
        for (s, e) in mhws:
            per_cell_mhw_B[s:e+1, lat, lon] = True

print(f"Per-cell MHW (interpretation B) cell-days: {per_cell_mhw_B.sum()}")

# Compare with interpretation A (my original)
per_cell_mhw_A = np.load('/tmp/per_cell_mhw.npy')
print(f"Per-cell MHW (interpretation A) cell-days: {per_cell_mhw_A.sum()}")
print(f"Difference: {(per_cell_mhw_A != per_cell_mhw_B).sum()} cells-days differ")

# Check regional events under interpretation B
active_B = per_cell_mhw_B.any(axis=(1, 2))
active_A = per_cell_mhw_A.any(axis=(1, 2))
print(f"\nActive days A: {active_A.sum()}, Active days B: {active_B.sum()}")
print(f"Active days A: {[i for i, a in enumerate(active_A) if a]}")
print(f"Active days B: {[i for i, a in enumerate(active_B) if a]}")

# Find events under B
events_B = []
in_event = False
for t in range(n_tgt):
    if active_B[t]:
        if not in_event:
            event_start = t
            in_event = True
    else:
        if in_event:
            events_B.append((event_start, t-1))
            in_event = False
if in_event:
    events_B.append((event_start, n_tgt-1))

print(f"\nEvents under B: {len(events_B)}")
tgt_start = pd.Timestamp('2007-06-01')
for onset, end in events_B:
    o = (tgt_start + pd.Timedelta(days=onset)).date()
    e = (tgt_start + pd.Timedelta(days=end)).date()
    print(f"  {o} to {e}")
