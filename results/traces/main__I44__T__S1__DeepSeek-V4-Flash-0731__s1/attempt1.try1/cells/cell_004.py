import fsspec
fs = fsspec.filesystem('onedata')
files = fs.ls('icsa2027_data_20261101T090944Z/s1z')
names = [f.split('/')[-1] for f in files]
names.sort()
import re
dates = []
for n in names:
    m = re.match(r'sst_(\d{4})(\d{2})(\d{2})\.nc', n)
    if m:
        dates.append((int(m.group(1)), int(m.group(2)), int(m.group(3))))
dates.sort()
print("First:", dates[0])
print("Last:", dates[-1])
print("Count:", len(dates))
# Check the date range
from collections import Counter
years = Counter(d[0] for d in dates)
print(years)
