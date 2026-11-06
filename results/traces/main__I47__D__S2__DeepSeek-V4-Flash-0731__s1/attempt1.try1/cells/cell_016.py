
import numpy as np
import pickle
from datetime import date, timedelta

def day_of_year(month, day):
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = sum(days_in_month[:month-1]) + day
    return doy

# Load data
tgt_data = np.load('/work/tgt_data.npy')  # (92, 60, 60)
tgt_time = np.load('/work/tgt_time.npy')
threshold_sm = np.load('/work/threshold_sm.npy')  # (366, 60, 60)
climatology_sm = np.load('/work/climatology_sm.npy')

# Get target dates as datetime objects
target_dates = [date(1970,1,1) + timedelta(days=int(t)) for t in tgt_time]
print("Target dates:", target_dates[0], "to", target_dates[-1])

# Compute day-of-year for each target date
target_doy = np.array([day_of_year(d.month, d.day) for d in target_dates])
print("Target DOY:", target_doy[0], "to", target_doy[-1])
# Verify: Jun 1 should be 153, Aug 31 should be 244
assert target_doy[0] == 153
assert target_doy[-1] == 244

# Sea cells
tgt_nan = np.isnan(tgt_data)
cell_tgt_nan = tgt_nan.any(axis=0)
sea_cells = ~cell_tgt_nan  # (60,60)
print("Sea cells:", sea_cells.sum())

# For each sea cell, determine hot days
n_t = len(target_dates)
n_lat = 60
n_lon = 60

# Hot mask: (92, 60, 60)
hot = np.zeros((n_t, n_lat, n_lon), dtype=bool)
for t in range(n_t):
    d = target_doy[t] - 1  # 0-indexed
    hot[t] = (tgt_data[t] >= threshold_sm[d]) & sea_cells

print("Hot day count:", hot.sum())

# For each cell, find per-cell MHWs
# mhw_mask: (92, 60, 60) - 1 where cell is inside a per-cell MHW
mhw_mask = np.zeros((n_t, n_lat, n_lon), dtype=np.uint8)

def find_mhws(hot_mask):
    T = len(hot_mask)
    runs = []
    i = 0
    while i < T:
        if hot_mask[i]:
            start = i
            while i < T and hot_mask[i]:
                i += 1
            runs.append((start, i-1))
        else:
            i += 1
    
    qualified = [r for r in runs if r[1]-r[0]+1 >= 5]
    
    if not qualified:
        return []
    
    merged = [qualified[0]]
    for run in qualified[1:]:
        prev = merged[-1]
        gap = run[0] - prev[1] - 1
        if 1 <= gap <= 2:
            merged[-1] = (prev[0], run[1])
        else:
            merged.append(run)
    
    return merged

# Compute per-cell MHWs
for i in range(n_lat):
    for j in range(n_lon):
        if sea_cells[i,j]:
            mhws = find_mhws(hot[:, i, j])
            for (s, e) in mhws:
                mhw_mask[s:e+1, i, j] = 1

print("MHW mask sum:", mhw_mask.sum())

# Determine regional events
# A day is active if at least one sea cell is inside a per-cell MHW on that day
active = mhw_mask.any(axis=(1,2))  # (92,)
print("Active days:", active.sum())

# Regional MHW events: maximal runs of consecutive active days
events = []
i = 0
while i < n_t:
    if active[i]:
        start = i
        while i < n_t and active[i]:
            i += 1
        events.append((start, i-1))
    else:
        i += 1

print("Regional events:", len(events))
for s, e in events:
    print(f"  {target_dates[s]} to {target_dates[e]} (days {s+1}-{e+1}, length {e-s+1})")
