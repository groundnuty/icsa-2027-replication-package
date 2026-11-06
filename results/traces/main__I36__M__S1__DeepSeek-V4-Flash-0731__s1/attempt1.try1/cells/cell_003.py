
import os, glob
files = sorted(os.listdir('/data/icsa2027_data_20261101T090944Z/s1z'))

# Extract dates from filenames
import re
dates = []
for f in files:
    m = re.match(r'sst_(\d{4})(\d{2})(\d{2})\.nc', f)
    if m:
        dates.append((int(m.group(1)), int(m.group(2)), int(m.group(3))))

# Check date range
print(f"Min date: {min(dates)}")
print(f"Max date: {max(dates)}")

# Check dates for baseline period: need 1991-12-27 to 2003-01-05
baseline_dates = [d for d in dates if (d[0], d[1], d[2]) >= (1991, 12, 27) and (d[0], d[1], d[2]) <= (2003, 1, 5)]
print(f"Baseline period files: {len(baseline_dates)}")
print(f"First: {min(baseline_dates)}")
print(f"Last: {max(baseline_dates)}")

# Check target period
target_dates = [d for d in dates if (d[0], d[1], d[2]) >= (2003, 6, 1) and (d[0], d[1], d[2]) <= (2003, 8, 31)]
print(f"Target period files: {len(target_dates)}")
print(f"First: {min(target_dates)}")
print(f"Last: {max(target_dates)}")
