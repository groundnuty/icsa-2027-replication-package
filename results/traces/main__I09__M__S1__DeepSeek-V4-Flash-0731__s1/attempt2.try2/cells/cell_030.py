
import numpy as np
from datetime import date, timedelta

# Verify pool construction and threshold for a specific case
# Pick doy 200 (July 19) for a specific sea cell

# Load baseline data
baseline_sst = np.load('/tmp/baseline_sst.npy')
baseline_dates_ord = np.load('/tmp/baseline_dates.npy')
baseline_dates = [date.fromordinal(int(o)) for o in baseline_dates_ord]

# Day-of-year mapping
month_days = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
cum_days = [0]
for md in month_days[:-1]:
    cum_days.append(cum_days[-1] + md)

def date_to_doy(d):
    return cum_days[d.month - 1] + d.day

# Verify doy for a few dates
test_cases = [
    (date(1992, 1, 1), 1),
    (date(1992, 2, 28), 59),
    (date(1992, 2, 29), 60),
    (date(1992, 3, 1), 61),
    (date(1993, 3, 1), 61),  # non-leap year
    (date(1992, 12, 31), 366),
    (date(1993, 12, 31), 366),
    (date(2022, 6, 1), 153),
    (date(2022, 8, 31), 244),
]

print("=== Day-of-year mapping verification ===")
for d, expected in test_cases:
    got = date_to_doy(d)
    status = "✓" if got == expected else "✗"
    print(f"  {d} -> doy {got} (expected {expected}) {status}")

# Verify pool for doy 200
print("\n=== Pool for doy 200 ===")
# Baseline dates with doy 200 in 1992-2002
baseline_dates_200 = []
for y in range(1992, 2003):
    for m in range(1, 13):
        for day in range(1, 32):
            try:
                dd = date(y, m, day)
                if date_to_doy(dd) == 200:
                    baseline_dates_200.append(dd)
            except ValueError:
                pass

print(f"Baseline dates with doy 200: {baseline_dates_200}")

# Check that the pool for doy 200 includes all dates within ±5 days
pool_dates_200 = set()
for d_base in baseline_dates_200:
    for offset in range(-5, 6):
        pool_dates_200.add(d_base + timedelta(days=offset))

print(f"Pool dates for doy 200: {len(pool_dates_200)} dates")
print(f"First: {min(pool_dates_200)}, Last: {max(pool_dates_200)}")

# Check that all pool dates are in the baseline data
date_set = set(baseline_dates)
missing = [d for d in pool_dates_200 if d not in date_set]
print(f"Pool dates missing from baseline data: {len(missing)}")
if missing:
    print(f"  Missing: {missing}")

# Verify threshold for cell (0,0) doy 200
# Get pool values
pool_idx = []
date_to_idx = {d: i for i, d in enumerate(baseline_dates)}
for d in sorted(pool_dates_200):
    pool_idx.append(date_to_idx[d])

pool_values = baseline_sst[pool_idx, 0, 0]
valid = pool_values[~np.isnan(pool_values)]
print(f"\nPool for cell (0,0) doy 200: {len(valid)} valid values out of {len(pool_values)}")
print(f"Pool values: {valid}")

# Compute 90th percentile with hazen method
p90 = np.quantile(valid, 0.9, method='hazen')
mean = np.mean(valid)
print(f"90th percentile (hazen): {p90}")
print(f"Mean: {mean}")

# Compare with what I computed
thresholds = np.load('/tmp/thresholds.npy')
climatology = np.load('/tmp/climatology.npy')
print(f"Stored threshold for doy 200, cell (0,0): {thresholds[199, 0, 0]}")
print(f"Stored climatology for doy 200, cell (0,0): {climatology[199, 0, 0]}")
print(f"Match: {np.isclose(p90, thresholds[199, 0, 0])} (threshold), {np.isclose(mean, climatology[199, 0, 0])} (climatology)")
