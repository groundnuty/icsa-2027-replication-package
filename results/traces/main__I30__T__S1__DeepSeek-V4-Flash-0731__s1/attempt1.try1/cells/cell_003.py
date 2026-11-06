
import fsspec, re
fs = fsspec.filesystem('onedata')
files = fs.ls('icsa2027_data_20261101T090944Z/s1z')
dates = []
for f in files:
    m = re.search(r'sst_(\d{8})\.nc', f)
    dates.append(m.group(1))
dates.sort()
print(len(dates))
print(dates[0], dates[-1])
