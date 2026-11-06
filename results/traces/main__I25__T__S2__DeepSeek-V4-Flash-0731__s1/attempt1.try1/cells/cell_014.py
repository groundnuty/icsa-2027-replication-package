
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict

def day_of_year(dt):
    cum_days_leap = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days_leap[dt.month - 1] + dt.day

start = datetime(1991, 12, 27)
end = datetime(2003, 1, 5)
all_loaded_dates = []
d = start
while d <= end:
    all_loaded_dates.append(d)
    d += timedelta(days=1)

date_to_idx = {dt: i for i, dt in enumerate(all_loaded_dates)}

pool_indices = defaultdict(set)
baseline_start = datetime(1992, 1, 1)
baseline_end = datetime(2002, 12, 31)

d = baseline_start
while d <= baseline_end:
    doy = day_of_year(d)
    if doy != 60:
        for offset in range(-5, 6):
            x = d + timedelta(days=offset)
            if x in date_to_idx:
                pool_indices[doy].add(date_to_idx[x])
    d += timedelta(days=1)

# Check if 2003-01-01 to 2003-01-05 are in any pool
for date_str in ['2003-01-01', '2003-01-02', '2003-01-03', '2003-01-04', '2003-01-05']:
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    idx = date_to_idx.get(dt)
    if idx is not None:
        # Find which pools this date belongs to
        pools = [day for day, indices in pool_indices.items() if idx in indices]
        print(f"{date_str}: belongs to pools for days {pools}")

# Also check 1991-12-27 to 1991-12-31
for date_str in ['1991-12-27', '1991-12-28', '1991-12-29', '1991-12-30', '1991-12-31']:
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    idx = date_to_idx.get(dt)
    if idx is not None:
        pools = [day for day, indices in pool_indices.items() if idx in indices]
        print(f"{date_str}: belongs to pools for days {pools}")
