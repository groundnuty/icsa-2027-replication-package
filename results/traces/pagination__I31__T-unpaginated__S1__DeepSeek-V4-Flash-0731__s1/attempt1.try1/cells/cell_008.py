
import datetime as dt

month_offsets = {1: 0, 2: 31, 3: 60, 4: 91, 5: 121, 6: 152, 7: 182, 8: 213, 9: 244, 10: 274, 11: 305, 12: 335}

def date_to_doy(y, m, d):
    return month_offsets[m] + d

# Find all baseline dates with each doy
baseline_start = dt.date(1992, 1, 1)
baseline_end = dt.date(2002, 12, 31)

# Map doy -> list of baseline dates
doy_to_baseline_dates = {d: [] for d in range(1, 367)}
d = baseline_start
while d <= baseline_end:
    doy = date_to_doy(d.year, d.month, d.day)
    doy_to_baseline_dates[doy].append(d)
    d += dt.timedelta(days=1)

# For each doy, find all dates D within ±5 days of baseline dates
# These are the dates whose SST goes into the pool for that doy
doy_to_pool_dates = {d: [] for d in range(1, 367)}

for doy in range(1, 367):
    if doy == 60:
        continue  # day 60 gets no pool of its own
    pool_dates = set()
    for B in doy_to_baseline_dates[doy]:
        for offset in range(-5, 6):
            D = B + dt.timedelta(days=offset)
            pool_dates.add(D)
    doy_to_pool_dates[doy] = sorted(pool_dates)

# Check a few
print("doy 1 pool dates count:", len(doy_to_pool_dates[1]))
print("First few:", doy_to_pool_dates[1][:10])
print("Last few:", doy_to_pool_dates[1][-10:])

print("\ndoy 59 pool dates count:", len(doy_to_pool_dates[59]))
print("First few:", doy_to_pool_dates[59][:10])
print("Last few:", doy_to_pool_dates[59][-10:])

# Check doy 60: should get its values from days 59 and 61 pools via the mean
print("\ndoy 60 baseline dates:", doy_to_baseline_dates[60])

# Check doy 61 pool
print("\ndoy 61 pool dates count:", len(doy_to_pool_dates[61]))
print("First few:", doy_to_pool_dates[61][:10])
print("Last few:", doy_to_pool_dates[61][-10:])

# Verify that Feb 29 dates (doy 60) are in the windows of nearby days
# Check if any Feb 29 in baseline years appears in pool of doy 59 or 61
feb29_dates = [dt.date(y, 2, 29) for y in [1992, 1996, 2000]]
for d in feb29_dates:
    print(f"\nFeb 29 {d.year}: in doy 59 pool? {d in doy_to_pool_dates[59]}, in doy 61 pool? {d in doy_to_pool_dates[61]}, in doy 58 pool? {d in doy_to_pool_dates[58]}, in doy 62 pool? {d in doy_to_pool_dates[62]}")
