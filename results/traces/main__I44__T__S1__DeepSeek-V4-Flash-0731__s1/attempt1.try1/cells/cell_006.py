import fsspec
fs = fsspec.filesystem('onedata')
files2 = fs.ls('icsa2027_data_20261101T090944Z/s2z')
print(len(files2))
names2 = [f.split('/')[-1] for f in files2]
names2.sort()
import re
dates = []
for n in names2:
    m = re.match(r'sst_(\d{4})(\d{2})(\d{2})\.nc', n)
    if m:
        dates.append((int(m.group(1)), int(m.group(2)), int(m.group(3))))
dates.sort()
print("First:", dates[0])
print("Last:", dates[-1])
print("Count:", len(dates))
from collections import Counter
years = Counter(d[0] for d in dates)
print(years)
