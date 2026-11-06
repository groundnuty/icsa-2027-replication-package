
import fsspec, re
fs = fsspec.filesystem('onedata')
files = fs.ls('icsa2027_data_20261101T090944Z/s1z')
print(f"Total files: {len(files)}")

# Check if files are sorted and look for gaps in dates
dates = []
for f in files:
    m = re.search(r'sst_(\d{4})(\d{2})(\d{2})\.nc$', f)
    if m:
        dates.append((int(m.group(1)), int(m.group(2)), int(m.group(3))))

dates.sort()
print(f"First: {dates[0]}, Last: {dates[-1]}")
print(f"Count: {len(dates)}")

# Check for gaps in the sequence
from datetime import date, timedelta
prev = date(*dates[0])
for d in dates[1:]:
    curr = date(*d)
    diff = (curr - prev).days
    if diff != 1:
        print(f"Gap: {prev} -> {curr}, diff={diff}")
    prev = curr
print("No gaps found" if len(dates) == 1000 else f"Found {len(dates)} dates")
