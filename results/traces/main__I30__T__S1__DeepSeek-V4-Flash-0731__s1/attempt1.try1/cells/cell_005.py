
import fsspec, re
fs = fsspec.filesystem('onedata')
# Check s2z
files = fs.ls('icsa2027_data_20261101T090944Z/s2z')
print(len(files))
dates=[]
for f in files:
    m = re.search(r'sst_(\d{8})\.nc', f)
    if m: dates.append(m.group(1))
dates.sort()
print(len(dates), dates[0], dates[-1])
