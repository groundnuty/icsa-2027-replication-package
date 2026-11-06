import fsspec
fs = fsspec.filesystem('onedata')
files = fs.ls('icsa2027_data_20261101T090944Z/s1z')
print(len(files))
# Check dates covered
import re
dates = []
for f in files:
    name = f.split('/')[-1]
    m = re.match(r'sst_(\d{8})\.nc', name)
    if m:
        dates.append(m.group(1))
dates.sort()
print(dates[0], dates[-1])
print(len(dates))
