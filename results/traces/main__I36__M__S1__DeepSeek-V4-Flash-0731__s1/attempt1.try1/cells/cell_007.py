
import os
import re
from datetime import date, timedelta

base_dir = '/data/icsa2027_data_20261101T090944Z/s1z'
files = sorted(os.listdir(base_dir))

# Extract dates from filenames
def parse_date(f):
    m = re.match(r'sst_(\d{4})(\d{2})(\d{2})\.nc', f)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None

all_dates = {}
for f in files:
    d = parse_date(f)
    if d:
        all_dates[d] = f

# Check completeness for baseline window and target
baseline_start = date(1991, 12, 27)
baseline_end = date(2003, 1, 5)
target_start = date(2003, 6, 1)
target_end = date(2003, 8, 31)

missing_baseline = []
d = baseline_start
while d <= baseline_end:
    if d not in all_dates:
        missing_baseline.append(d)
    d += timedelta(days=1)
print(f"Missing baseline dates: {len(missing_baseline)}")
if missing_baseline:
    print(f"First few: {missing_baseline[:5]}")

missing_target = []
d = target_start
while d <= target_end:
    if d not in all_dates:
        missing_target.append(d)
    d += timedelta(days=1)
print(f"Missing target dates: {len(missing_target)}")
if missing_target:
    print(f"First few: {missing_target[:5]}")

# Count total files needed
count = 0
d = baseline_start
while d <= baseline_end:
    if d in all_dates:
        count += 1
    d += timedelta(days=1)
print(f"Baseline files available: {count}")

count = 0
d = target_start
while d <= target_end:
    if d in all_dates:
        count += 1
    d += timedelta(days=1)
print(f"Target files available: {count}")
