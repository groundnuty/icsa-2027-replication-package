
import numpy as np
import pandas as pd
import xarray as xr

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
time = pd.to_datetime(ds.time.values)

mask = (time >= pd.Timestamp('1991-12-27')) & (time <= pd.Timestamp('2003-01-05'))
idx_base = np.where(mask)[0]
base_time = time[idx_base]

def date_to_doy(dt):
    month = dt.month
    day = dt.day
    days_before = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return days_before[month-1] + day

# Build pool indices
base_dates_mask = (base_time >= pd.Timestamp('1992-01-01')) & (base_time <= pd.Timestamp('2002-12-31'))
base_dates = base_time[base_dates_mask]
base_doys = np.array([date_to_doy(d) for d in base_dates])

all_pool_dates = set()
for d in range(1, 367):
    if d == 60:
        continue
    bd_mask = (base_doys == d)
    bd_dates = base_dates[bd_mask]
    if len(bd_dates) == 0:
        continue
    for B in bd_dates:
        for delta in range(-5, 6):
            all_pool_dates.add(B + pd.Timedelta(days=delta))

# Sort and find range
all_pool_dates_sorted = sorted(all_pool_dates)
print(f"Total unique dates in all pools: {len(all_pool_dates_sorted)}")
print(f"First date used: {all_pool_dates_sorted[0]}")
print(f"Last date used: {all_pool_dates_sorted[-1]}")

# Check which dates from the full window [1991-12-27, 2003-01-05] are NOT in any pool
full_window_dates = set(base_time)
not_used = sorted(full_window_dates - all_pool_dates)
print(f"Dates in full window but not in any pool: {len(not_used)}")
for d in not_used[:10]:
    print(f"  {d}")

# Check which dates from the full window ARE in pools but weren't loaded
# Actually, all dates in [1991-12-27, 2003-01-05] should be in the data
print(f"\nAll dates in pools range: {all_pool_dates_sorted[0]} to {all_pool_dates_sorted[-1]}")
print(f"First date in full window: {base_time[0]}")
print(f"Last date in full window: {base_time[-1]}")
