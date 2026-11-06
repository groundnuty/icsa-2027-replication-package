
import numpy as np
import pickle
from datetime import date, timedelta

def day_of_year(month, day):
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = sum(days_in_month[:month-1]) + day
    return doy

# Load data (cast to float64)
base_data = np.load('/work/base_data.npy').astype(np.float64)  # (4028, 60, 60)
tgt_data = np.load('/work/tgt_data.npy').astype(np.float64)    # (92, 60, 60)
tgt_time = np.load('/work/tgt_time.npy')
with open('/work/pool_dates.pkl', 'rb') as f:
    pool_dates = pickle.load(f)

# Compute threshold and climatology
n_lat = base_data.shape[1]
n_lon = base_data.shape[2]

threshold = np.zeros((366, n_lat, n_lon), dtype=np.float64)
climatology = np.zeros((366, n_lat, n_lon), dtype=np.float64)

for d in range(1, 367):
    if d == 60:
        continue
    idx = np.array(pool_dates[d])
    pool = base_data[idx]
    threshold[d-1] = np.nanpercentile(pool, 90, method='hazen', axis=0)
    climatology[d-1] = np.nanmean(pool, axis=0)

threshold[59] = (threshold[58] + threshold[60]) / 2.0
climatology[59] = (climatology[58] + climatology[60]) / 2.0

# Smoothing
def smooth_wrap(arr):
    n = arr.shape[0]
    padded = np.concatenate([arr[-15:], arr, arr[:15]], axis=0)
    result = np.zeros_like(arr)
    for i in range(n):
        result[i] = np.nanmean(padded[i:i+31], axis=0)
    return result

threshold_sm = smooth_wrap(threshold)
climatology_sm = smooth_wrap(climatology)

# Target dates
target_dates = [date(1970,1,1) + timedelta(days=int(t)) for t in tgt_time]
target_doy = np.array([day_of_year(d.month, d.day) for d in target_dates])

# Sea cells
tgt_nan = np.isnan(tgt_data)
cell_tgt_nan = tgt_nan.any(axis=0)
sea_cells = ~cell_tgt_nan

# Hot mask
n_t = len(target_dates)
hot = np.zeros((n_t, n_lat, n_lon), dtype=bool)
for t in range(n_t):
    d = target_doy[t] - 1
    hot[t] = (tgt_data[t] >= threshold_sm[d]) & sea_cells

# Per-cell MHW detection with correct gap counting
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
        # Count non-hot days between prev end and run start
        gap_days = range(prev[1]+1, run[0])
        non_hot_count = sum(not hot_mask[t] for t in gap_days)
        if 1 <= non_hot_count <= 2:
            merged[-1] = (prev[0], run[1])
        else:
            merged.append(run)
    
    return merged

mhw_mask = np.zeros((n_t, n_lat, n_lon), dtype=np.uint8)
for i in range(n_lat):
    for j in range(n_lon):
        if sea_cells[i,j]:
            mhws = find_mhws(hot[:, i, j])
            for (s, e) in mhws:
                mhw_mask[s:e+1, i, j] = 1

# Regional events
active = mhw_mask.any(axis=(1,2))
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

print("Number of events:", len(events))
for s, e in events:
    print(f"  {target_dates[s]} to {target_dates[e]} (days {s+1}-{e+1})")

print("MHW mask sum:", mhw_mask.sum())
print("Active days:", active.sum())
print("Sea cells:", sea_cells.sum())

# Save
np.save('/work/mhw_mask.npy', mhw_mask)
np.save('/work/sea_cells.npy', sea_cells)
np.save('/work/hot.npy', hot)
print("Saved intermediate results")
