
import numpy as np
import pandas as pd
import json

# Load data
baseline_data = np.load('/tmp/baseline_data.npy').astype(np.float64)
target_data = np.load('/tmp/target_data.npy').astype(np.float64)
baseline_times = np.load('/tmp/baseline_times.npy').astype('datetime64[D]')
target_times = np.load('/tmp/target_times.npy').astype('datetime64[D]')
lat_vals = np.load('/tmp/lat_vals.npy')
lon_vals = np.load('/tmp/lon_vals.npy')

# Rebuild everything
def day_of_year(month, day):
    month_days = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(month_days[:month-1]) + day

time_index_map = {}
for i, t in enumerate(baseline_times):
    time_index_map[t] = i

sea_mask = ~np.any(np.isnan(target_data), axis=0)
n_lat, n_lon = sea_mask.shape

target_doy = np.array([day_of_year(pd.Timestamp(t).month, pd.Timestamp(t).day) for t in target_times])

pool_indices = {}
month_days_const = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
for d in range(1, 367):
    if d == 60:
        continue
    indices = set()
    for year in range(1992, 2003):
        remaining = d
        month = 0
        while remaining > month_days_const[month]:
            remaining -= month_days_const[month]
            month += 1
        day = remaining
        month += 1
        is_leap = (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0))
        if month == 2 and day == 29 and not is_leap:
            continue
        b_date = np.datetime64(f'{year}-{month:02d}-{day:02d}', 'D')
        for offset in range(-5, 6):
            date_i = b_date + np.timedelta64(offset, 'D')
            if date_i in time_index_map:
                indices.add(time_index_map[date_i])
    pool_indices[d] = sorted(indices)

n_doy = 366
threshold = np.full((n_doy, n_lat, n_lon), np.nan)
climatology = np.full((n_doy, n_lat, n_lon), np.nan)

sea_ij = np.where(sea_mask)
sea_pairs = list(zip(sea_ij[0], sea_ij[1]))

for d in range(1, 367):
    if d == 60:
        continue
    idx = pool_indices[d]
    pool_data = baseline_data[idx, :, :]
    for i, j in sea_pairs:
        vals = pool_data[:, i, j]
        vals = vals[~np.isnan(vals)]
        if len(vals) > 0:
            threshold[d-1, i, j] = np.quantile(vals, 0.9, method='hazen')
            climatology[d-1, i, j] = np.mean(vals)

threshold[59, :, :] = (threshold[58, :, :] + threshold[60, :, :]) / 2
climatology[59, :, :] = (climatology[58, :, :] + climatology[60, :, :]) / 2

# Smooth with 31-day centered moving mean that wraps
def smooth_wrap(arr):
    result = np.zeros_like(arr)
    for d in range(366):
        total = 0.0
        count = 0
        for offset in range(-15, 16):
            idx = (d + offset) % 366
            if not np.isnan(arr[idx]):
                total += arr[idx]
                count += 1
        if count > 0:
            result[d] = total / count
        else:
            result[d] = np.nan
    return result

threshold_smooth = np.full_like(threshold, np.nan)
climatology_smooth = np.full_like(climatology, np.nan)

for i, j in sea_pairs:
    threshold_smooth[:, i, j] = smooth_wrap(threshold[:, i, j])
    climatology_smooth[:, i, j] = smooth_wrap(climatology[:, i, j])

print("Threshold smooth NaN count for sea cells:", np.sum(np.isnan(threshold_smooth[:, sea_mask])))
print("Climatology smooth NaN count for sea cells:", np.sum(np.isnan(climatology_smooth[:, sea_mask])))

# ============================================
# Step 5: Per-cell MHWs
# ============================================
n_time = target_data.shape[0]

# A day is hot if SST >= threshold
hot = np.zeros((n_time, n_lat, n_lon), dtype=bool)
for t in range(n_time):
    doy = target_doy[t]
    thr = threshold_smooth[doy-1, :, :]
    hot[t, :, :] = (target_data[t, :, :] >= thr) & sea_mask

print("Hot count:", hot.sum())

# Per-cell MHW: run of >= 5 consecutive hot days, joined if separated by 1-2 non-hot days
mhw_mask = np.zeros((n_time, n_lat, n_lon), dtype=np.uint8)

for i, j in sea_pairs:
    hot_series = hot[:, i, j]
    
    # Find runs of consecutive hot days
    runs = []
    in_run = False
    start = 0
    for t in range(n_time):
        if hot_series[t]:
            if not in_run:
                in_run = True
                start = t
        else:
            if in_run:
                runs.append((start, t-1))
                in_run = False
    if in_run:
        runs.append((start, n_time-1))
    
    # Filter runs with >= 5 days
    mhw_runs = [r for r in runs if r[1] - r[0] + 1 >= 5]
    
    # Join runs separated by 1 or 2 non-hot days
    if mhw_runs:
        joined = [list(mhw_runs[0])]
        for k in range(1, len(mhw_runs)):
            prev_end = joined[-1][1]
            curr_start = mhw_runs[k][0]
            gap = curr_start - prev_end - 1
            if gap <= 2:
                joined[-1][1] = mhw_runs[k][1]
            else:
                joined.append(list(mhw_runs[k]))
        
        for (s, e) in joined:
            mhw_mask[s:e+1, i, j] = 1

print("MHW mask count:", mhw_mask.sum())

# ============================================
# Step 6: Regional events
# ============================================
active = np.any(mhw_mask > 0, axis=(1, 2))
print("Active days:", active.sum(), "of", n_time)

events = []
in_event = False
start = 0
for t in range(n_time):
    if active[t]:
        if not in_event:
            in_event = True
            start = t
    else:
        if in_event:
            events.append((start, t-1))
            in_event = False
if in_event:
    events.append((start, n_time-1))

print("Regional events:", len(events))
event_list = []
for (s, e) in events:
    onset = pd.Timestamp(target_times[s]).strftime('%Y-%m-%d')
    end = pd.Timestamp(target_times[e]).strftime('%Y-%m-%d')
    print(f"  {onset} to {end} ({e-s+1} days)")
    event_list.append({"onset": onset, "end": end})

# Save results
np.save('/tmp/threshold_smooth.npy', threshold_smooth)
np.save('/tmp/climatology_smooth.npy', climatology_smooth)
np.save('/tmp/mhw_mask.npy', mhw_mask)
np.save('/tmp/sea_mask.npy', sea_mask)
print("Saved intermediate results.")
