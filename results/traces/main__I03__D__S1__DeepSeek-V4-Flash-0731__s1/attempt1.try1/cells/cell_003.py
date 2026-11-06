
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

# Check which dates we need: baseline 1992-2002 (plus window), and target 2014-06-01 to 2014-08-31
# Are these files in our list?
import datetime
# Check if we have 2014 files
d2014 = [d for d in dates if d.startswith('2014')]
print(f"2014 files: {len(d2014)}")
if d2014:
    print(f"First 2014: {d2014[0]}, Last 2014: {d2014[-1]}")

# Check 1992-2002
d92_02 = [d for d in dates if 1992 <= int(d[:4]) <= 2002]
print(f"1992-2002 files: {len(d92_02)}")

# Check 1991 and 2003
d91 = [d for d in dates if d.startswith('1991')]
d03 = [d for d in dates if d.startswith('2003')]
print(f"1991 files: {len(d91)}, 2003 files: {len(d03)}")
