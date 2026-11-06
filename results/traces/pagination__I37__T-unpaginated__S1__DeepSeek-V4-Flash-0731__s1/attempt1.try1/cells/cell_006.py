
import datetime

# Check if baseline dates are complete
baseline_start = datetime.date(1991, 12, 27)
baseline_end = datetime.date(2003, 1, 5)

# Generate expected dates
expected = []
d = baseline_start
while d <= baseline_end:
    expected.append(d)
    d += datetime.timedelta(days=1)

print(f"Expected baseline days: {len(expected)}")

import fsspec
import re
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
files = fs.ls(base)

dates = []
for f in files:
    m = re.search(r'sst_(\d{4})(\d{2})(\d{2})\.nc', f)
    if m:
        dates.append(datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3))))

date_set = set(dates)
missing = [d for d in expected if d not in date_set]
print(f"Missing baseline days: {len(missing)}")
if missing:
    print("First few missing:", missing[:10])

# Check target dates
target_start = datetime.date(2012, 6, 1)
target_end = datetime.date(2012, 8, 31)
expected_target = []
d = target_start
while d <= target_end:
    expected_target.append(d)
    d += datetime.timedelta(days=1)
missing_target = [d for d in expected_target if d not in date_set]
print(f"Missing target days: {len(missing_target)}")
