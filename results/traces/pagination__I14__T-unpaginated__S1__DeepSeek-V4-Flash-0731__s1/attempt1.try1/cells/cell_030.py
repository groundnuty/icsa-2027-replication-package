
import numpy as np
from datetime import date, timedelta

# Rebuild pool indices and check which dates are used
def day_of_year_fixed(y, m, d):
    if m == 1:
        return d
    elif m == 2:
        return 31 + d
    else:
        days_before_month = {3: 60, 4: 91, 5: 121, 6: 152, 7: 182, 8: 213, 9: 244, 10: 274, 11: 305, 12: 335}
        return days_before_month[m] + d

full_range_start = date(1991, 12, 27)
full_range_end = date(2003, 1, 5)
all_dates = []
d = full_range_start
while d <= full_range_end:
    all_dates.append(d)
    d += timedelta(days=1)
date_to_idx = {d: i for i, d in enumerate(all_dates)}

baseline_start = date(1992, 1, 1)
baseline_end = date(2002, 12, 31)
baseline_dates_by_doy = {}
d = baseline_start
while d <= baseline_end:
    doy = day_of_year_fixed(d.year, d.month, d.day)
    if doy != 60:
        if doy not in baseline_dates_by_doy:
            baseline_dates_by_doy[doy] = []
        baseline_dates_by_doy[doy].append(d)
    d += timedelta(days=1)

# Find all dates that are used in any pool
used_indices = set()
for doy in range(1, 367):
    if doy == 60:
        continue
    for bd in baseline_dates_by_doy.get(doy, []):
        for offset in range(-5, 6):
            nd = bd + timedelta(days=offset)
            if full_range_start <= nd <= full_range_end:
                used_indices.add(date_to_idx[nd])

used_dates = sorted([all_dates[i] for i in used_indices])
print(f"Dates used in any pool: {len(used_dates)}")
print(f"First used date: {used_dates[0]}")
print(f"Last used date: {used_dates[-1]}")

# Check if 1991-12-27 is used
print(f"\n1991-12-27 used: {date(1991,12,27) in used_dates}")
print(f"2003-01-05 used: {date(2003,1,5) in used_dates}")

# Check if all dates in range are used
all_in_range = set(all_dates)
unused = all_in_range - set(used_dates)
if unused:
    print(f"\nUnused dates ({len(unused)}):")
    for d in sorted(unused)[:20]:
        print(f"  {d}")
else:
    print(f"\nAll {len(all_dates)} dates in range are used.")
