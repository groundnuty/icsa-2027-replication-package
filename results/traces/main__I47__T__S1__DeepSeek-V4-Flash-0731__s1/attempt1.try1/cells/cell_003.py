
import fsspec, re
fs = fsspec.filesystem('onedata')
files = fs.ls('icsa2027_data_20261101T090944Z/s1z')
# Extract years and dates from filenames
dates = []
for f in files:
    m = re.search(r'sst_(\d{4})(\d{2})(\d{2})\.nc', f)
    if m:
        dates.append((int(m.group(1)), int(m.group(2)), int(m.group(3))))
print(len(dates))
years = sorted(set(d[0] for d in dates))
print("Years:", years)
# Check date range
print("First:", dates[0])
print("Last:", dates[-1])
# Count per year
from collections import Counter
c = Counter(d[0] for d in dates)
for y in sorted(c):
    print(y, c[y])
