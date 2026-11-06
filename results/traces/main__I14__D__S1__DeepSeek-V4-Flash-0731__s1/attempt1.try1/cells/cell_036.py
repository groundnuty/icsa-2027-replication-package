
import numpy as np
import pandas as pd

# Load baseline times
baseline_times = np.load('/work/baseline_times.npy')
baseline_pd = pd.to_datetime(baseline_times)

# Check that all dates from 1992-01-01 to 2002-12-31 are present
start = pd.Timestamp('1992-01-01')
end = pd.Timestamp('2002-12-31')
expected_dates = pd.date_range(start, end, freq='D')
actual_dates = baseline_pd[(baseline_pd >= start) & (baseline_pd <= end)]

print(f"Expected baseline dates: {len(expected_dates)}")
print(f"Actual baseline dates in data: {len(actual_dates)}")

# Check for missing dates
missing = expected_dates[~expected_dates.isin(actual_dates)]
print(f"Missing dates: {len(missing)}")
if len(missing) > 0:
    print(f"First few missing: {missing[:5]}")

# Also check target dates
target_times = np.load('/work/target_times.npy')
target_pd = pd.to_datetime(target_times)
expected_target = pd.date_range('2015-06-01', '2015-08-31', freq='D')
print(f"\nExpected target dates: {len(expected_target)}")
print(f"Actual target dates in data: {len(target_pd)}")
missing_target = expected_target[~expected_target.isin(target_pd)]
print(f"Missing target dates: {len(missing_target)}")
