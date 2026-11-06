
import numpy as np

# Reload data
target_sst = np.load('output/target_sst.npy')
sea_cells = np.load('output/sea_cells.npy')
threshold_smooth = np.load('output/threshold_smooth.npy')
target_dates = np.load('output/target_dates.npy')

starts = [0, 0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]

# Compute day of year for each target date
from datetime import datetime, timezone
doy_values = []
for i in range(len(target_dates)):
    ts = target_dates[i].astype('datetime64[ns]').astype(np.int64) / 1e9
    td = datetime.fromtimestamp(ts, tz=timezone.utc)
    d_doy = starts[td.month] + td.day
    doy_values.append(d_doy)
doy_values = np.array(doy_values)

# Get thresholds for target days
thresholds_for_target = threshold_smooth[doy_values - 1]  # (92, 60, 60)

# Determine hot days
hot = (target_sst >= thresholds_for_target) & sea_cells[np.newaxis, :, :]

n_days, n_lat, n_lon = hot.shape

# Correct implementation:
# 1. Find runs of >= 5 consecutive hot days (these are per-cell MHWs)
# 2. Join per-cell MHWs separated by 1 or 2 non-hot days

mhw_mask = np.zeros_like(hot, dtype=np.uint8)

for lat in range(n_lat):
    for lon in range(n_lon):
        if not sea_cells[lat, lon]:
            continue
        
        h = hot[:, lat, lon]
        
        # Find all runs of hot days
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
        
        # Filter to runs >= 5 days (these are initial MHWs)
        mhws = [r for r in runs if r[1] - r[0] + 1 >= 5]
        
        # Join MHWs separated by 1 or 2 non-hot days
        joined = []
        for mhw in mhws:
            if joined:
                prev = joined[-1]
                gap = mhw[0] - prev[1] - 1
                if 1 <= gap <= 2:
                    prev[1] = mhw[1]  # Join, gap days become part of MHW
                else:
                    joined.append(mhw.copy())
            else:
                joined.append(mhw.copy())
        
        # Mark MHW days
        for start, end in joined:
            mhw_mask[start:end+1, lat, lon] = 1

print(f"MHW mask sum: {mhw_mask.sum()}")

# Check how many cells have MHWs
cells_with_mhw = (mhw_mask.sum(axis=0) > 0).sum()
print(f"Cells with MHW: {cells_with_mhw}")

# Check per-cell MHW counts
for lat in range(n_lat):
    for lon in range(n_lon):
        if sea_cells[lat, lon] and mhw_mask[:, lat, lon].sum() > 0:
            runs = []
            h = mhw_mask[:, lat, lon]
            i = 0
            while i < n_days:
                if h[i]:
                    s = i
                    while i < n_days and h[i]:
                        i += 1
                    runs.append((s, i-1))
                else:
                    i += 1
            if runs:
                print(f"Cell ({lat},{lon}): MHW runs: {runs}")
                break  # Just show one example

# Save
np.save('output/mhw_mask.npy', mhw_mask)

# Compute regional events
active = mhw_mask.sum(axis=(1, 2)) > 0
print(f"\nActive days: {active.sum()} / {n_days}")

events = []
i = 0
while i < n_days:
    if active[i]:
        start = i
        while i < n_days and active[i]:
            i += 1
        end = i - 1
        events.append((start, end))
    else:
        i += 1

print(f"Regional events: {len(events)}")
for start, end in events:
    ts1 = target_dates[start].astype('datetime64[ns]').astype(np.int64) / 1e9
    ts2 = target_dates[end].astype('datetime64[ns]').astype(np.int64) / 1e9
    onset = datetime.fromtimestamp(ts1, tz=timezone.utc)
    end_dt = datetime.fromtimestamp(ts2, tz=timezone.utc)
    print(f"  Event: {onset.date()} to {end_dt.date()} ({end-start+1} days)")
