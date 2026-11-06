
import numpy as np
from datetime import datetime, timedelta

# Load data
target_sst = np.load('output/target_sst.npy')
sea_cells = np.load('output/sea_cells.npy')
threshold_smooth = np.load('output/threshold_smooth.npy')

# Day-of-year mapping
starts = [0, 0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]

# Load target dates
from datetime import datetime
target_dates = np.load('output/target_dates.npy')
print(f"Target dates: {len(target_dates)}")

# Compute day of year for each target date
doy_values = []
for i in range(len(target_dates)):
    td = datetime.utcfromtimestamp(target_dates[i].astype('datetime64[ns]').astype(np.int64) / 1e9)
    d_doy = starts[td.month] + td.day
    doy_values.append(d_doy)
doy_values = np.array(doy_values)
print(f"Day of year values: {doy_values}")

# For each target day, get the threshold for each cell
# threshold_smooth shape: (366, 60, 60)
thresholds_for_target = threshold_smooth[doy_values - 1]  # (92, 60, 60)

# Determine hot days: SST >= threshold
# Only for sea cells
hot = np.zeros_like(target_sst, dtype=bool)
hot = target_sst >= thresholds_for_target
hot = hot & sea_cells[np.newaxis, :, :]

print(f"Hot days count: {hot.sum()} / {hot.size}")

# Now find per-cell MHWs
# For each cell, find runs of >=5 consecutive hot days
# Then join runs separated by 1-2 non-hot days

n_days, n_lat, n_lon = hot.shape

# mhw_mask: 1 where cell is in an MHW, 0 otherwise
mhw_mask = np.zeros_like(hot, dtype=np.uint8)

for lat in range(n_lat):
    for lon in range(n_lon):
        if not sea_cells[lat, lon]:
            continue
        
        h = hot[:, lat, lon]  # (92,) boolean
        
        # Find runs of hot days
        runs = []
        i = 0
        while i < n_days:
            if h[i]:
                start = i
                while i < n_days and h[i]:
                    i += 1
                end = i - 1
                runs.append([start, end])
            else:
                i += 1
        
        if not runs:
            continue
        
        # Join runs separated by 1 or 2 non-hot days
        joined = [runs[0].copy()]
        for r in runs[1:]:
            prev = joined[-1]
            gap = r[0] - prev[1] - 1
            if 1 <= gap <= 2:
                prev[1] = r[1]  # Join
            else:
                joined.append(r.copy())
        
        # Filter to runs of >= 5 days
        for start, end in joined:
            if end - start + 1 >= 5:
                mhw_mask[start:end+1, lat, lon] = 1

print(f"MHW mask sum: {mhw_mask.sum()}")

# Save
np.save('output/mhw_mask.npy', mhw_mask)
print("Saved MHW mask")
