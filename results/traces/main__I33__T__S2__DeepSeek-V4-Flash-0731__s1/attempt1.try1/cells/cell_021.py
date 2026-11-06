
import numpy as np
import xarray as xr
import pandas as pd

# Load saved data
target_data = xr.open_dataset('target_data.nc')
thresholds_smooth = np.load('thresholds_smooth.npy')

target_sst = target_data.analysed_sst.values
target_time = target_data.time.values
n_days, n_lat, n_lon = target_sst.shape

cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]

def date_to_doy(year, month, day):
    return cum_days[month-1] + day

target_dates = [pd.Timestamp(t).date() for t in target_time.astype('datetime64[D]')]
target_doys = [date_to_doy(d.year, d.month, d.day) for d in target_dates]

# Sea cells
sea_mask = np.all(~np.isnan(target_sst), axis=0)

# Hot days
threshold_for_target = np.array([thresholds_smooth[doy] for doy in target_doys])
hot = (target_sst >= threshold_for_target) & sea_mask[np.newaxis, :, :]

# Per-cell MHW detection
mhw_mask = np.zeros_like(hot, dtype=np.uint8)

for i in range(n_lat):
    for j in range(n_lon):
        if not sea_mask[i, j]:
            continue
        hot_cell = hot[:, i, j]
        
        # Find runs of consecutive hot days
        runs = []
        in_run = False
        run_start = 0
        for d in range(n_days):
            if hot_cell[d]:
                if not in_run:
                    run_start = d
                    in_run = True
            else:
                if in_run:
                    runs.append((run_start, d - 1))
                    in_run = False
        if in_run:
            runs.append((run_start, n_days - 1))
        
        # Keep only runs of >= 5 days
        runs = [r for r in runs if r[1] - r[0] + 1 >= 5]
        
        # Join runs separated by 1 or 2 non-hot days
        if len(runs) > 0:
            joined_runs = [list(runs[0])]
            for k in range(1, len(runs)):
                gap = runs[k][0] - joined_runs[-1][1] - 1
                if gap <= 2:
                    joined_runs[-1][1] = runs[k][1]
                else:
                    joined_runs.append(list(runs[k]))
            
            for start, end in joined_runs:
                mhw_mask[start:end+1, i, j] = 1

# Regional events
# A day is active if at least one sea cell is in a per-cell MHW
active = mhw_mask.sum(axis=(1, 2)) > 0
print("Active days:", np.sum(active))

# Find regional events (maximal runs of consecutive active days)
events = []
in_event = False
event_start = 0
for d in range(n_days):
    if active[d]:
        if not in_event:
            event_start = d
            in_event = True
    else:
        if in_event:
            events.append((event_start, d - 1))
            in_event = False
if in_event:
    events.append((event_start, n_days - 1))

print("Regional events:")
for start, end in events:
    print(f"  {target_dates[start]} to {target_dates[end]}")
    print(f"  Days {start} to {end}, duration {end-start+1}")

# Check for any inactive days
print("\nInactive days:")
for d in range(n_days):
    if not active[d]:
        print(f"  Day {d} ({target_dates[d]}): {mhw_mask.sum(axis=(1,2))[d]} cells in MHW")
