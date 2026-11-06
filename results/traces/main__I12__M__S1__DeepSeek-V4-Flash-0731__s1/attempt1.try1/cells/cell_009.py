
from datetime import date, timedelta

def day_of_year(d):
    month = d.month
    day = d.day
    days_in_month = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = sum(days_in_month[:month]) + day
    if month > 2:
        doy += 1
    return doy

# Build pool dates for each day of year
baseline_start = date(1992, 1, 1)
baseline_end = date(2002, 12, 31)

# For each day of year d (1-366, d != 60), find pool dates
pool_dates = {}

# First, find all baseline dates and their day of year
baseline_dates = []
d = baseline_start
while d <= baseline_end:
    baseline_dates.append(d)
    d += timedelta(days=1)

print(f"Baseline dates: {len(baseline_dates)}")

# Group baseline dates by day of year
baseline_by_doy = {}
for bd in baseline_dates:
    doy = day_of_year(bd)
    if doy not in baseline_by_doy:
        baseline_by_doy[doy] = []
    baseline_by_doy[doy].append(bd)

print("Days of year present:", sorted(baseline_by_doy.keys()))
print("Day 60 count:", len(baseline_by_doy.get(60, [])))

# Build pool for each day of year (except 60)
for doy in range(1, 367):
    if doy == 60:
        continue
    dates_in_pool = set()
    for bd in baseline_by_doy.get(doy, []):
        for i in range(-5, 6):
            dates_in_pool.add(bd + timedelta(days=i))
    pool_dates[doy] = sorted(dates_in_pool)

# Check some examples
print("\nDay 1 (Jan 1) pool size:", len(pool_dates[1]))
print("First few:", pool_dates[1][:5], "...", pool_dates[1][-5:])

print("\nDay 152 (Jun 1) pool size:", len(pool_dates[152]))
print("First few:", pool_dates[152][:5], "...", pool_dates[152][-5:])

print("\nDay 366 (Dec 31) pool size:", len(pool_dates[366]))
print("First few:", pool_dates[366][:5], "...", pool_dates[366][-5:])

# Total pool sizes
total = sum(len(v) for v in pool_dates.values())
print("\nTotal pool entries:", total)
