
import fsspec
fs = fsspec.filesystem('onedata')
files = fs.ls('icsa2027_data_20261101T090944Z/s1z')
print(f"Total files: {len(files)}")

# Extract dates from filenames
import re
dates = []
for f in files:
    m = re.search(r'sst_(\d{4})(\d{2})(\d{2})\.nc', f)
    if m:
        dates.append((int(m.group(1)), int(m.group(2)), int(m.group(3))))

dates.sort()
years = set(d[0] for d in dates)
print(f"Years: {sorted(years)}")
print(f"First: {dates[0]}, Last: {dates[-1]}")
print(f"Count per year:")
from collections import Counter
print(Counter(d[0] for d in dates))
