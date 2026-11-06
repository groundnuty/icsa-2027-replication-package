
import numpy as np
import pandas as pd

base_times = np.load('/work/base_times.npy')
base_dates = pd.DatetimeIndex(base_times)

def date_to_doy(dt):
    year, month, day = dt.year, dt.month, dt.day
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = sum(days_in_month[m] for m in range(0, month-1)) + day
    return doy

base_doy = np.array([date_to_doy(d) for d in base_dates])

# Check pool for doy 366 (Dec 31)
mask_92_02 = (base_dates >= pd.Timestamp('1992-01-01')) & (base_dates <= pd.Timestamp('2002-12-31'))
mask_doy366 = mask_92_02 & (base_doy == 366)
dates_doy366 = base_dates[mask_doy366]
print(f"Baseline dates with doy 366: {len(dates_doy366)}")

pool_mask = np.zeros(len(base_dates), dtype=bool)
for bd in dates_doy366:
    start = bd - pd.Timedelta(days=5)
    end = bd + pd.Timedelta(days=5)
    pool_mask |= (base_dates >= start) & (base_dates <= end)

pool_dates = base_dates[pool_mask]
print(f"Pool for doy 366: {len(pool_dates)} dates")
jan03 = pool_dates[(pool_dates.year == 2003)]
print(f"Jan 2003 dates in pool: {jan03}")
