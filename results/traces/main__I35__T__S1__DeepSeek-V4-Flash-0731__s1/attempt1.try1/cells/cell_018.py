
import numpy as np
import datetime

# Load data
baseline_sst = np.load('/tmp/baseline_sst.npy')  # (4028, 60, 60)
target_sst = np.load('/tmp/target_sst.npy')       # (92, 60, 60)
baseline_times = np.load('/tmp/baseline_times.npy')
target_times = np.load('/tmp/target_times.npy')

# Convert to dates
baseline_dates = [np.datetime64(t).astype('datetime64[D]').astype(object) for t in baseline_times]
target_dates = [np.datetime64(t).astype('datetime64[D]').astype(object) for t in target_times]

# Verify baseline dates
print(f"Baseline first: {baseline_dates[0]}")
print(f"Baseline last: {baseline_dates[-1]}")
print(f"Baseline count: {len(baseline_dates)}")

# Check if all dates from 1991-12-27 to 2003-01-05 are present
import calendar
expected_dates = []
d = datetime.date(1991, 12, 27)
end = datetime.date(2003, 1, 5)
while d <= end:
    expected_dates.append(d)
    d += datetime.timedelta(days=1)
print(f"Expected dates: {len(expected_dates)}")
print(f"Actual dates: {len(baseline_dates)}")
print(f"All present: {all(ed == bd for ed, bd in zip(expected_dates, baseline_dates))}")

# Check target dates
d = datetime.date(2009, 6, 1)
end = datetime.date(2009, 8, 31)
expected_target = []
while d <= end:
    expected_target.append(d)
    d += datetime.timedelta(days=1)
print(f"\nExpected target: {len(expected_target)}")
print(f"Actual target: {len(target_dates)}")
print(f"All present: {all(ed == bd for ed, bd in zip(expected_target, target_dates))}")
