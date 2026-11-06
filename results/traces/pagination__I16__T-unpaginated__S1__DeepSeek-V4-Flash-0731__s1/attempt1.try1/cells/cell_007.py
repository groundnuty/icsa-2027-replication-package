
import fsspec
import re
from datetime import date, timedelta

fs = fsspec.filesystem('onedata')
files = fs.ls('icsa2027_data_20261101T090944Z/s1z')
files_set = set()
for fp in files:
    name = fp.split('/')[-1]
    m = re.match(r'sst_(\d{4})(\d{2})(\d{2})\.nc', name)
    if m:
        files_set.add((int(m.group(1)), int(m.group(2)), int(m.group(3))))

# Check baseline range: 1991-12-27 to 2003-01-05
baseline_start = date(1991, 12, 27)
baseline_end = date(2003, 1, 5)
missing = []
d = baseline_start
while d <= baseline_end:
    if (d.year, d.month, d.day) not in files_set:
        missing.append(d)
    d += timedelta(days=1)
print('Missing baseline files:', len(missing))
if missing:
    print(missing[:10])

# Check target range: 2008-06-01 to 2008-08-31
target_start = date(2008, 6, 1)
target_end = date(2008, 8, 31)
missing_t = []
d = target_start
while d <= target_end:
    if (d.year, d.month, d.day) not in files_set:
        missing_t.append(d)
    d += timedelta(days=1)
print('Missing target files:', len(missing_t))
if missing_t:
    print(missing_t[:10])
