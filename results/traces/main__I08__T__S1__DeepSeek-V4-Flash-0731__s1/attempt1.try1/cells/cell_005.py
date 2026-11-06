
import fsspec
import re
fs = fsspec.filesystem('onedata')
files = fs.ls('icsa2027_data_20261101T090944Z/s2z')
print(len(files))
print(files[:5])
print(files[-5:])
dates = []
for f in files:
    m = re.search(r'sst_(\d{8})\.nc', f)
    if m:
        dates.append(m.group(1))
from collections import Counter
years = Counter(d[:4] for d in dates)
print(dict(sorted(years.items())))
