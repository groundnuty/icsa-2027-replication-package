
import os
files = os.listdir('/data/icsa2027_data_20261101T090944Z/s1z')
print("Number of files:", len(files))

# Extract dates from filenames
import re
dates = []
for f in files:
    m = re.match(r'sst_(\d{8})\.nc', f)
    if m:
        dates.append(m.group(1))

dates.sort()
print("First:", dates[0])
print("Last:", dates[-1])
print("Total dates:", len(dates))

# Check coverage by year
from collections import Counter
years = Counter(d[:4] for d in dates)
for y in sorted(years):
    print(f"  {y}: {years[y]} days")
