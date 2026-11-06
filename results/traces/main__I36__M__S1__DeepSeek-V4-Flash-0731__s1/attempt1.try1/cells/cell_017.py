
import numpy as np
from datetime import date, timedelta

# Load data
baseline_data = np.load('/tmp/baseline_data.npy')
with open('/tmp/baseline_dates.txt') as f:
    baseline_dates = [date.fromisoformat(line.strip()) for line in f]
date_to_idx = {d: i for i, d in enumerate(baseline_dates)}

def day_of_year(d):
    month_days = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return d.day + sum(month_days[:d.month])

# Verify pool for doy 153 (June 1)
# Expected dates: May 27 - June 6 for each year 1992-2002
pool_dates = []
for y in range(1992, 2003):
    b = date(y, 6, 1)
    for t in range(-5, 6):
        pool_dates.append(b + timedelta(days=t))

print(f"Number of pool dates for doy 153: {len(pool_dates)}")
print(f"First few: {pool_dates[:5]}")
print(f"Last few: {pool_dates[-5:]}")
print(f"All in baseline: {all(d in date_to_idx for d in pool_dates)}")

# Get the actual pool data for cell (30, 30)
pool_idx = [date_to_idx[d] for d in pool_dates]
pool_data = baseline_data[pool_idx, 30, 30]
valid = pool_data[~np.isnan(pool_data)]
print(f"Valid values for cell (30,30) doy 153: {len(valid)}")
if len(valid) > 0:
    print(f"Mean: {np.mean(valid)}")
    print(f"P90 (hazen): {np.quantile(valid, 0.9, method='hazen')}")
    print(f"Stored climatology: {np.load('/tmp/climatology_raw.npy')[152, 30, 30]}")
    print(f"Stored threshold: {np.load('/tmp/threshold_raw.npy')[152, 30, 30]}")
