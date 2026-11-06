
import numpy as np
import pandas as pd

# Load data
time_int = np.load('/tmp/time_sub.npy')
time_sub = time_int.astype('datetime64[s]')

def date_to_doy(date):
    ts = pd.Timestamp(date)
    month, day = ts.month, ts.day
    cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[month-1] + day

dates = pd.to_datetime(time_sub)
n_time = len(dates)

# Rebuild pool masks to check edge dates
baseline_start = pd.Timestamp('1992-01-01')
baseline_end = pd.Timestamp('2002-12-31')
baseline_dates = pd.date_range(baseline_start, baseline_end, freq='D')

pool_masks = {}
for d in range(1, 367):
    if d == 60:
        continue
    pool_masks[d] = np.zeros(n_time, dtype=bool)

for B in baseline_dates:
    d = date_to_doy(B)
    if d == 60:
        continue
    B_start = B - pd.Timedelta(days=5)
    B_end = B + pd.Timedelta(days=5)
    mask = (dates >= B_start) & (dates <= B_end)
    pool_masks[d] |= mask

# Check earliest and latest dates in any pool
all_pool_dates = []
for d in range(1, 367):
    if d == 60:
        continue
    idx = np.where(pool_masks[d])[0]
    if len(idx) > 0:
        all_pool_dates.extend(idx)

all_pool_dates = np.array(sorted(set(all_pool_dates)))
earliest_pool = dates[all_pool_dates[0]]
latest_pool = dates[all_pool_dates[-1]]
print(f"Earliest date in any pool: {earliest_pool}")
print(f"Latest date in any pool: {latest_pool}")

# Check specific dates
for check_date in [pd.Timestamp('1991-12-27'), pd.Timestamp('1992-01-01'), 
                   pd.Timestamp('2002-12-31'), pd.Timestamp('2003-01-05')]:
    # Find which DOY pools this date belongs to
    doys = []
    for d in range(1, 367):
        if d == 60:
            continue
        if pool_masks[d][np.where(dates == check_date)[0][0]]:
            doys.append(d)
    print(f"{check_date.strftime('%Y-%m-%d')} (DOY {date_to_doy(check_date)}): in pools for DOYs {doys}")
