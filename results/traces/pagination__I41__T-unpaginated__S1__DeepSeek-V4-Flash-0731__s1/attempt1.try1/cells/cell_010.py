
import datetime
import numpy as np

def day_of_year(d):
    doy = (d - datetime.date(d.year, 1, 1)).days + 1
    is_leap = (d.year % 4 == 0 and (d.year % 100 != 0 or d.year % 400 == 0))
    if not is_leap and d.month >= 3:
        doy += 1
    return doy

# Generate all baseline dates
baseline_start = datetime.date(1991, 12, 27)
baseline_end = datetime.date(2003, 1, 5)
all_baseline_dates = []
d = baseline_start
while d <= baseline_end:
    all_baseline_dates.append(d)
    d += datetime.timedelta(days=1)

n_baseline = len(all_baseline_dates)
print(f"Total baseline dates: {n_baseline}")

# Compute day-of-year for each baseline date
baseline_doy = np.array([day_of_year(d) for d in all_baseline_dates])

# For each day-of-year (1-366 except 60), build the pool mask
# The pool for d includes baseline date X if there exists a baseline date Y
# with doy(Y)=d and |X - Y| <= 5 days.

# First, find the index of each date in the baseline array
date_to_idx = {d: i for i, d in enumerate(all_baseline_dates)}

# For each d, find baseline dates with doy=d
doy_to_baseline_idxs = {}
for i, doy in enumerate(baseline_doy):
    if doy not in doy_to_baseline_idxs:
        doy_to_baseline_idxs[doy] = []
    doy_to_baseline_idxs[doy].append(i)

# Build pool masks for each d (except 60)
pool_masks = {}
for d in range(1, 367):
    if d == 60:
        continue
    mask = np.zeros(n_baseline, dtype=bool)
    if d in doy_to_baseline_idxs:
        for idx in doy_to_baseline_idxs[d]:
            # Include all dates within ±5 days
            date_y = all_baseline_dates[idx]
            for offset in range(-5, 6):
                date_x = date_y + datetime.timedelta(days=offset)
                if date_x in date_to_idx:
                    mask[date_to_idx[date_x]] = True
    pool_masks[d] = mask
    print(f"Day {d}: pool size = {mask.sum()}")

# Check a few
print("\nDay 1 pool size:", pool_masks[1].sum())
print("Day 59 pool size:", pool_masks[59].sum())
print("Day 61 pool size:", pool_masks[61].sum())
print("Day 366 pool size:", pool_masks[366].sum())
print("Day 2 pool size:", pool_masks[2].sum())
