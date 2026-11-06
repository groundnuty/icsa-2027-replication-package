
import numpy as np
import pandas as pd
from datetime import timedelta

mhw_mask = np.load('/tmp/mhw_mask.npy')  # This might not exist, let me redo

# Actually let me reload and redo everything in one go
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Load all needed data
threshold_smooth = np.load('/tmp/threshold_smooth.npy')
sea_mask = np.load('/tmp/sea_mask.npy')
target_sst = np.load('/tmp/target_sst.npy')
target_time = np.load('/tmp/target_time.npy')

def doy_from_date(dt):
    month_days_cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return month_days_cum[dt.month - 1] + dt.day

target_dates = [pd.Timestamp(t).to_pydatetime() for t in target_time]
target_doy = np.array([doy_from_date(d) for d in target_dates])
target_sst64 = target_sst.astype(np.float64)

n_time = len(target_dates)
n_lat, n_lon = 60, 60

# Hot matrix
hot = np.zeros((n_time, n_lat, n_lon), dtype=bool)
for t in range(n_time):
    doy = target_doy[t] - 1
    thr = threshold_smooth[doy]
    sst_t = target_sst64[t]
    hot[t] = (sst_t >= thr) & sea_mask

np.save('/tmp/hot.npy', hot)

# Per-cell MHW detection
mhw_mask = np.zeros_like(hot)

for lat_i in range(n_lat):
    for lon_j in range(n_lon):
        if not sea_mask[lat_i, lon_j]:
            continue
        
        h = hot[:, lat_i, lon_j]
        
        # Find runs of consecutive hot days
        runs = []
        i = 0
        while i < n_time:
            if h[i]:
                start = i
                while i < n_time and h[i]:
                    i += 1
                end = i - 1
                runs.append((start, end))
            else:
                i += 1
        
        # MHWs: runs with length >= 5
        mhws = [(s, e) for s, e in runs if (e - s + 1) >= 5]
        
        if not mhws:
            continue
        
        # Join MHWs separated by 1 or 2 non-hot days
        joined = []
        current = list(mhws[0])
        for next_mhw in mhws[1:]:
            gap = next_mhw[0] - current[1] - 1
            if 1 <= gap <= 2:
                current[1] = next_mhw[1]
            else:
                joined.append(tuple(current))
                current = list(next_mhw)
        joined.append(tuple(current))
        
        # Mark all days in joined MHWs
        for s, e in joined:
            mhw_mask[s:e+1, lat_i, lon_j] = True

np.save('/tmp/mhw_mask.npy', mhw_mask)
print("mhw_mask shape:", mhw_mask.shape)
print("Total MHW days:", mhw_mask.sum())

# Regional events
# A day is active if at least one sea cell is inside a per-cell MHW
active = mhw_mask.any(axis=(1, 2))  # shape: (n_time,)
print("Active days:", active)
print("Number of active days:", active.sum())

# Find maximal runs of consecutive active days
events = []
i = 0
while i < n_time:
    if active[i]:
        start = i
        while i < n_time and active[i]:
            i += 1
        end = i - 1
        events.append((start, end))
    else:
        i += 1

print("Regional events:", len(events))
for s, e in events:
    print(f"  Event: {target_dates[s].strftime('%Y-%m-%d')} to {target_dates[e].strftime('%Y-%m-%d')}, length {e-s+1} days")
