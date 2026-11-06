
import numpy as np
import datetime

def day_of_year(date):
    y, m, d = date.year, date.month, date.day
    months = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    is_leap = (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0)
    doy = sum(months[:m-1]) + d
    if m > 2 and is_leap:
        doy += 1
    if not is_leap and m > 2:
        doy += 1
    return doy

# Check all dates loaded
baseline_dates = [datetime.date.fromordinal(int(d)) for d in np.load('cache/baseline_dates.npy')]
print(f'Loaded dates: {len(baseline_dates)} from {baseline_dates[0]} to {baseline_dates[-1]}')

# All dates in range 1991-12-27 to 2003-01-05
all_start = datetime.date(1991, 12, 27)
all_end = datetime.date(2003, 1, 5)
expected_dates = []
d = all_start
while d <= all_end:
    expected_dates.append(d)
    d += datetime.timedelta(days=1)

print(f'Expected dates: {len(expected_dates)} from {expected_dates[0]} to {expected_dates[-1]}')
print(f'All loaded: {set(baseline_dates) == set(expected_dates)}')

# Verify every expected date is in some pool
baseline_start = datetime.date(1992, 1, 1)
baseline_end = datetime.date(2002, 12, 31)

all_pool_dates = set()
for doy in range(1, 367):
    if doy == 60:
        continue
    centers = []
    dy = baseline_start
    while dy <= baseline_end:
        if day_of_year(dy) == doy:
            centers.append(dy)
        dy += datetime.timedelta(days=1)
    
    for c in centers:
        for k in range(-5, 6):
            all_pool_dates.add(c + datetime.timedelta(days=k))

print(f'Dates in all pools: {len(all_pool_dates)}')
print(f'All loaded dates in pools: {set(baseline_dates) == all_pool_dates}')
