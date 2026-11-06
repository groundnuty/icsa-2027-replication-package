
import numpy as np
import xarray as xr
import pandas as pd

# Load the output mask
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
mhw = ds.mhw.values
time_vals = ds.time.values

# Get all cells in MHWs during the first event (June 11-16, indices 10-15)
cells_june = set()
for t in range(10, 16):
    for ci, cj in np.argwhere(mhw[t] == 1):
        cells_june.add((ci, cj))

print(f"Cells in June event: {len(cells_june)}")
for ci, cj in sorted(cells_june):
    print(f"  ({ci}, {cj})")

# For each cell, find the range of days in MHW
print("\nMHW periods for June event cells:")
for ci, cj in sorted(cells_june):
    days = np.where(mhw[:, ci, cj] == 1)[0]
    if len(days) > 0:
        start_date = pd.Timestamp(time_vals[days[0]]).strftime('%Y-%m-%d')
        end_date = pd.Timestamp(time_vals[days[-1]]).strftime('%Y-%m-%d')
        print(f"  Cell ({ci},{cj}): {start_date} to {end_date} ({len(days)} days)")

# Verify that each cell in MHW has >=5 consecutive hot days (or joined runs)
# Load necessary data for hot detection
target_sst = np.load('/work/target_sst.npy')
thresholds_smooth = np.load('/work/thresholds_smooth.npy')
target_time_idx = np.load('/work/target_time_idx.npy')

ds2 = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
time_full = ds2.time.values
target_dates_full = time_full[target_time_idx]
ds2.close()
target_dates_list = [pd.Timestamp(t).to_pydatetime().date() for t in target_dates_full]

def doy_from_date(date):
    m = date.month; d = date.day
    if m == 1: return d
    elif m == 2: return 31 + d
    elif m == 3: return 60 + d
    elif m == 4: return 91 + d
    elif m == 5: return 121 + d
    elif m == 6: return 152 + d
    elif m == 7: return 182 + d
    elif m == 8: return 213 + d
    elif m == 9: return 244 + d
    elif m == 10: return 274 + d
    elif m == 11: return 305 + d
    elif m == 12: return 335 + d

target_doy = [doy_from_date(d) for d in target_dates_list]
n_target = len(target_dates_list)

target_sst64 = target_sst.astype(np.float64)

# Check hot patterns for all cells in June event
print("\nVerifying hot patterns for June event cells:")
for ci, cj in sorted(cells_june):
    hot_days = []
    for t in range(n_target):
        thresh = thresholds_smooth[target_doy[t]-1, ci, cj]
        if target_sst64[t, ci, cj] >= thresh:
            hot_days.append(t)
    
    # Find runs of consecutive hot days
    runs = []
    start = None
    for t in hot_days:
        if start is None:
            start = t
        elif t != start + len(runs):
            # Actually, this logic is wrong. Let me fix.
            pass
    
    # Simpler: find runs
    runs = []
    i = 0
    while i < len(hot_days):
        start = hot_days[i]
        end = start
        while i + 1 < len(hot_days) and hot_days[i+1] == end + 1:
            i += 1
            end = hot_days[i]
        runs.append((start, end))
        i += 1
    
    # Check if any run >= 5, or if runs can be joined (gap <= 2)
    qualified = False
    for s, e in runs:
        if e - s + 1 >= 5:
            qualified = True
            break
    
    if not qualified:
        # Check if joined runs qualify
        for k in range(len(runs)):
            for l in range(k+1, len(runs)):
                gap = runs[l][0] - runs[k][1] - 1
                if gap <= 2:
                    if runs[l][1] - runs[k][0] + 1 >= 5:
                        qualified = True
                        break
    
    print(f"  Cell ({ci},{cj}): hot days={hot_days}, runs={runs}, qualified={qualified}")
