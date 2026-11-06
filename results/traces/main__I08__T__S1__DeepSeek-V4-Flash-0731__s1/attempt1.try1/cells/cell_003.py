
import fsspec
import re
fs = fsspec.filesystem('onedata')
files = fs.ls('icsa2027_data_20261101T090944Z/s1z')
# Extract dates from filenames
dates = []
for f in files:
    m = re.search(r'sst_(\d{8})\.nc', f)
    if m:
        dates.append(m.group(1))
print(len(dates))
print(dates[0], dates[-1])
# Group by year
from collections import Counter
years = Counter(d[:4] for d in dates)
print(dict(sorted(years.items())))
