
import numpy as np
from datetime import date, timedelta

month_days = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
cum_days = [0]
for md in month_days[:-1]:
    cum_days.append(cum_days[-1] + md)

def date_to_doy(d):
    return cum_days[d.month - 1] + d.day

target_start = date(2022, 6, 1)
target_end = date(2022, 8, 31)
target_dates = []
d = target_start
while d <= target_end:
    target_dates.append(d)
    d += timedelta(days=1)

doy_values = [date_to_doy(d) for d in target_dates]
print(f"Target dates: {target_dates[0]} to {target_dates[-1]}")
print(f"Day of year for each target date:")
for i, (d, doy) in enumerate(zip(target_dates, doy_values)):
    print(f"  {d}: doy {doy}")
