
import numpy as np
import pandas as pd

# Rebuild the pool for doy 59 and inspect dates
def date_to_doy(dt):
    month = dt.month
    day = dt.day
    days_before = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return days_before[month-1] + day

# Baseline dates 1992-01-01 to 2002-12-31
base_dates = pd.date_range('1992-01-01', '2002-12-31', freq='D')
base_doys = np.array([date_to_doy(d) for d in base_dates])

# Pool for doy 59
d = 59
bd_mask = (base_doys == d)
bd_dates = base_dates[bd_mask]
print(f"Doy {d}: {len(bd_dates)} baseline dates")
for B in bd_dates:
    print(f"  {B.strftime('%Y-%m-%d')}")

# Collect all dates in pool
pool_date_set = set()
for B in bd_dates:
    for delta in range(-5, 6):
        pool_date_set.add(B + pd.Timedelta(days=delta))

pool_dates_list = sorted(pool_date_set)
print(f"Pool has {len(pool_dates_list)} dates")
for dt in pool_dates_list:
    print(f"  {dt.strftime('%Y-%m-%d')}")
