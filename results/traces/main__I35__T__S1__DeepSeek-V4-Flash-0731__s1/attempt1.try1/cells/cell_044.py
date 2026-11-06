
import numpy as np
import datetime

# Load float64 data
target_sst = np.load('/tmp/target_sst_f64.npy')  # (92, 60, 60)
target_times = np.load('/tmp/target_times.npy')
threshold_smooth = np.load('/tmp/threshold_smooth_f64.npy')  # (366, 60, 60)
sea_mask = np.load('/tmp/sea_mask.npy')

target_dates = [np.datetime64(t).astype('datetime64[D]').astype(object) for t in target_times]

def day_of_year(dt):
    month = dt.month
    day = dt.day
    days_before = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return days_before[month-1] + day

target_doy = np.array([day_of_year(d) for d in target_dates])
print(f"Target day-of-years: {target_doy}")

# Compute hot days
n_time, n_lat, n_lon = target_sst.shape
hot_mask = np.zeros((n_time, n_lat, n_lon), dtype=bool)

for t in range(n_time):
    doy = target_doy[t]
    thresh = threshold_smooth[doy-1, :, :]
    sst = target_sst[t, :, :]
    hot_mask[t] = (sst >= thresh) & np.isfinite(sst) & np.isfinite(thresh)

print(f"Hot days sum: {hot_mask.sum()}")

# MHW detection: first find runs >= 5 hot days, then join MHWs separated by 1-2 non-hot days
mhw_mask = np.zeros((n_time, n_lat, n_lon), dtype=np.uint8)

for i in range(n_lat):
    for j in range(n_lon):
        if not sea_mask[i,j]:
            continue
        hot = hot_mask[:, i, j]
        
        # Find all runs of consecutive hot days
        runs = []
        start = None
        for t in range(n_time):
            if hot[t]:
                if start is None:
                    start = t
            else:
                if start is not None:
                    runs.append((start, t-1))
                    start = None
        if start is not None:
            runs.append((start, n_time-1))
        
        # Keep only runs >= 5 days
        mhws = [(s, e) for (s, e) in runs if e - s + 1 >= 5]
        
        if not mhws:
            continue
        
        # Join MHWs separated by 1-2 non-hot days
        joined = []
        current_start = mhws[0][0]
        current_end = mhws[0][1]
        
        for k in range(1, len(mhws)):
            gap = mhws[k][0] - current_end - 1
            if gap <= 2:
                current_end = mhws[k][1]
            else:
                joined.append((current_start, current_end))
                current_start = mhws[k][0]
                current_end = mhws[k][1]
        joined.append((current_start, current_end))
        
        for (s, e) in joined:
            mhw_mask[s:e+1, i, j] = 1

print(f"MHW mask sum: {mhw_mask.sum()}")

# Regional events
active = mhw_mask.sum(axis=(1, 2)) > 0
print(f"Active days: {np.where(active)[0]}")

events = []
start = None
for t in range(len(active)):
    if active[t]:
        if start is None:
            start = t
    else:
        if start is not None:
            events.append((start, t-1))
            start = None
if start is not None:
    events.append((start, len(active)-1))

print(f"Regional events: {len(events)}")
for s, e in events:
    print(f"  {target_dates[s]} to {target_dates[e]}, length={e-s+1} days")

np.save('/tmp/mhw_mask_f64.npy', mhw_mask)
print("Saved")
