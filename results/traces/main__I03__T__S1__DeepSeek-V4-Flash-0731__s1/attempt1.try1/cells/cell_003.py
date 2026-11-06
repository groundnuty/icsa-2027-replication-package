
import fsspec
import re
fs = fsspec.filesystem('onedata')
files = fs.ls('icsa2027_data_20261101T090944Z/s1z')
# Extract dates from filenames
dates = set()
for f in files:
    m = re.search(r'sst_(\d{4})(\d{2})(\d{2})\.nc', f)
    if m:
        dates.add((int(m.group(1)), int(m.group(2)), int(m.group(3))))
dates = sorted(dates)
print("Number of files:", len(dates))
print("First:", dates[0])
print("Last:", dates[-1])
# Check if we have the needed range
# Need baseline 1991-12-27 to 2003-01-05, and target 2014-06-01 to 2014-08-31
import datetime
# Find all dates in needed ranges
baseline_start = datetime.date(1991,12,27)
baseline_end = datetime.date(2003,1,5)
target_start = datetime.date(2014,6,1)
target_end = datetime.date(2014,8,31)

date_set = set()
for y,m,d in dates:
    date_set.add(datetime.date(y,m,d))

# Check coverage
missing_baseline = []
for i in range((baseline_end - baseline_start).days + 1):
    d = baseline_start + datetime.timedelta(days=i)
    if d not in date_set:
        missing_baseline.append(d)
print("Missing baseline days:", len(missing_baseline))
if missing_baseline:
    print(missing_baseline[:10])

missing_target = []
for i in range((target_end - target_start).days + 1):
    d = target_start + datetime.timedelta(days=i)
    if d not in date_set:
        missing_target.append(d)
print("Missing target days:", len(missing_target))
if missing_target:
    print(missing_target[:10])

# What is the overall range?
print("Overall first:", dates[0], "Last:", dates[-1])
