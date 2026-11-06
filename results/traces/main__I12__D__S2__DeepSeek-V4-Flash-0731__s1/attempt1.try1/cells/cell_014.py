
import numpy as np
import pandas as pd
import xarray as xr

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
time = pd.to_datetime(ds.time.values)

# Check the actual pool dates for doys 59 and 61
mask = (time >= pd.Timestamp('1991-12-27')) & (time <= pd.Timestamp('2003-01-05'))
idx_base = np.where(mask)[0]
base_time = time[idx_base]

def date_to_doy(dt):
    month = dt.month
    day = dt.day
    days_before = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return days_before[month-1] + day

# Baseline dates
base_dates_mask = (base_time >= pd.Timestamp('1992-01-01')) & (base_time <= pd.Timestamp('2002-12-31'))
base_dates = base_time[base_dates_mask]
base_doys = np.array([date_to_doy(d) for d in base_dates])

# Pool for doy 59: dates within ±5 days of Feb 28 in baseline years
for d in [59, 61]:
    bd_mask = (base_doys == d)
    bd_dates = base_dates[bd_mask]
    print(f"\nDoy {d}: {len(bd_dates)} baseline dates")
    for B in bd_dates:
        print(f"  {B.strftime('%Y-%m-%d')}")
    
    # Collect all dates in pool
    pool_date_set = set()
    for B in bd_dates:
        for delta in range(-5, 6):
            pool_date_set.add(B + pd.Timedelta(days=delta))
    
    pool_dates_list = sorted(pool_date_set)
    print(f"  Pool has {len(pool_dates_list)} dates")
    # Count Feb 29 dates in pool
    feb29 = [d for d in pool_dates_list if d.month == 2 and d.day == 29]
    print(f"  Feb 29 dates in pool: {len(feb29)}")
    for d in feb29:
        print(f"    {d.strftime('%Y-%m-%d')}")
