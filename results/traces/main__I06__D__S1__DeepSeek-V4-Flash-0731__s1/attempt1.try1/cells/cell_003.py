
import fsspec
fs = fsspec.filesystem('onedata')
files = fs.ls('icsa2027_data_20261101T090944Z/s1z')
# Extract dates from filenames
import re
dates = []
for f in files:
    m = re.search(r'sst_(\d{8})\.nc', f)
    if m:
        dates.append(m.group(1))
dates.sort()
print(f"First: {dates[0]}")
print(f"Last: {dates[-1]}")
print(f"Count: {len(dates)}")

# Check which dates we need: baseline 1992-2002 (plus window), and target 2012-06-01 to 2012-08-31
# Are any of these in the file list?
baseline_dates = []
import datetime
# baseline: 1992-01-01 to 2002-12-31, plus window 1991-12-27 to 1991-12-31 and 2003-01-01 to 2003-01-05
start = datetime.date(1991, 12, 27)
end = datetime.date(2003, 1, 5)
d = start
while d <= end:
    baseline_dates.append(d.strftime('%Y%m%d'))
    d += datetime.timedelta(days=1)

target_dates = []
start = datetime.date(2012, 6, 1)
end = datetime.date(2012, 8, 31)
d = start
while d <= end:
    target_dates.append(d.strftime('%Y%m%d'))
    d += datetime.timedelta(days=1)

# Check overlap
baseline_in_files = set(baseline_dates) & set(dates)
target_in_files = set(target_dates) & set(dates)
print(f"Baseline dates in files: {len(baseline_in_files)} of {len(baseline_dates)}")
print(f"Target dates in files: {len(target_in_files)} of {len(target_dates)}")

# What dates are actually in the files?
print(f"All dates range: {dates[0]} to {dates[-1]}")
