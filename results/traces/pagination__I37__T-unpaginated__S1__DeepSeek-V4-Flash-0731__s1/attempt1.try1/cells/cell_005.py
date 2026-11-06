
import fsspec
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
files = fs.ls(base)
print(f"Total files: {len(files)}")

# Parse dates from filenames
import re
dates = []
for f in files:
    m = re.search(r'sst_(\d{4})(\d{2})(\d{2})\.nc', f)
    if m:
        dates.append((int(m.group(1)), int(m.group(2)), int(m.group(3))))

dates.sort()
print(f"Date range: {dates[0]} to {dates[-1]}")
print(f"Number of parsed dates: {len(dates)}")

# Check for duplicate dates
from collections import Counter
date_counts = Counter(dates)
dups = {k: v for k, v in date_counts.items() if v > 1}
print(f"Duplicate dates: {len(dups)}")

# Check coverage of key periods
import datetime
date_objs = [datetime.date(y, m, d) for y, m, d in dates]

# Baseline years 1992-2002
baseline_start = datetime.date(1991, 12, 27)
baseline_end = datetime.date(2003, 1, 5)
baseline_dates = [d for d in date_objs if baseline_start <= d <= baseline_end]
print(f"Baseline period dates available: {len(baseline_dates)}")

# Target period
target_start = datetime.date(2012, 6, 1)
target_end = datetime.date(2012, 8, 31)
target_dates = [d for d in date_objs if target_start <= d <= target_end]
print(f"Target period dates available: {len(target_dates)}")
