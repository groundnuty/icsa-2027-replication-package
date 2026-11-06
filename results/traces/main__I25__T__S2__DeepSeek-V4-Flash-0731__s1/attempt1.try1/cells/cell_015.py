
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

# Check if Feb 29 values are in pools of days 59 and 61
# Feb 29, 1992: day 60
# Its window as a baseline date doesn't contribute (since day 60 has no pool)
# But Feb 29, 1992 should be in the pools of days 59 (Feb 28) and 61 (Mar 1) etc.
# because it's within ±5 days of Feb 28 and Mar 1 dates.

for year in [1992, 1996, 2000]:
    feb29 = datetime(year, 2, 29)
    idx = date_to_idx.get(feb29)
    if idx is not None:
        pools = sorted([day for day, indices in pool_indices.items() if idx in indices])
        print(f"Feb 29, {year}: belongs to pools for days {pools}")
