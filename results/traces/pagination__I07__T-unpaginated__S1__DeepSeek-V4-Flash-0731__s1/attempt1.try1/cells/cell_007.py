
import fsspec

fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
files = fs.ls(base)
print(f"Total files: {len(files)}")

# Check first and last files
import re
dates = []
for f in files:
    m = re.search(r'sst_(\d{8})\.nc$', f)
    if m:
        dates.append(m.group(1))
dates.sort()
print(f"First: {dates[0]}, Last: {dates[-1]}")
print(f"Total date files: {len(dates)}")

# Check baseline files exist
# 1991-12-27 to 2003-01-05
import datetime
start_b = datetime.date(1991, 12, 27)
end_b = datetime.date(2003, 1, 5)
d = start_b
baseline_dates = []
while d <= end_b:
    baseline_dates.append(d.strftime('%Y%m%d'))
    d += datetime.timedelta(days=1)
print(f"Baseline dates needed: {len(baseline_dates)}")

# Check target files
start_t = datetime.date(2021, 6, 1)
end_t = datetime.date(2021, 8, 31)
d = start_t
target_dates = []
while d <= end_t:
    target_dates.append(d.strftime('%Y%m%d'))
    d += datetime.timedelta(days=1)
print(f"Target dates needed: {len(target_dates)}")

# Check all needed files exist
all_needed = set(baseline_dates) | set(target_dates)
existing = set(dates)
missing = all_needed - existing
print(f"Missing files: {len(missing)}")
if missing:
    print(sorted(missing)[:10])
