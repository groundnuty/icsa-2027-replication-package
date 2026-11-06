
import datetime as dt

month_offsets = {1: 0, 2: 31, 3: 60, 4: 91, 5: 121, 6: 152, 7: 182, 8: 213, 9: 244, 10: 274, 11: 305, 12: 335}

def date_to_doy(y, m, d):
    return month_offsets[m] + d

baseline_start = dt.date(1992, 1, 1)
baseline_end = dt.date(2002, 12, 31)

doy_to_baseline_dates = {d: [] for d in range(1, 367)}
d = baseline_start
while d <= baseline_end:
    doy = date_to_doy(d.year, d.month, d.day)
    doy_to_baseline_dates[doy].append(d)
    d += dt.timedelta(days=1)

all_pool_dates = set()
for doy in range(1, 367):
    if doy == 60:
        continue
    for B in doy_to_baseline_dates[doy]:
        for offset in range(-5, 6):
            all_pool_dates.add(B + dt.timedelta(days=offset))

# Check what dates in the full range are covered
full_range_start = dt.date(1991, 12, 27)
full_range_end = dt.date(2003, 1, 5)
d = full_range_start
missing = []
while d <= full_range_end:
    if d not in all_pool_dates:
        missing.append(d)
    d += dt.timedelta(days=1)

print(f"Total unique dates in all pools: {len(all_pool_dates)}")
print(f"Missing dates in range: {len(missing)}")
if missing:
    print("Missing:", missing[:20])

# Also check if any dates outside 1991-12-27 to 2003-01-05 are needed
print(f"Min pool date: {min(all_pool_dates)}")
print(f"Max pool date: {max(all_pool_dates)}")
