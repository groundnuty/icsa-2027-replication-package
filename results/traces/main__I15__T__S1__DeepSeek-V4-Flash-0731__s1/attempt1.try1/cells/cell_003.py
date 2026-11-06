import fsspec
import re
fs = fsspec.filesystem('onedata')
files = fs.ls('icsa2027_data_20261101T090944Z/s1z')
# Extract dates from filenames
dates = []
for f in files:
    m = re.search(r'sst_(\d{4})(\d{2})(\d{2})\.nc', f)
    if m:
        dates.append((int(m.group(1)), int(m.group(2)), int(m.group(3))))
dates.sort()
print("First:", dates[0])
print("Last:", dates[-1])
print("Count:", len(dates))

# Group by year
from collections import Counter
years = Counter(d[0] for d in dates)
for y in sorted(years):
    print(y, years[y])
