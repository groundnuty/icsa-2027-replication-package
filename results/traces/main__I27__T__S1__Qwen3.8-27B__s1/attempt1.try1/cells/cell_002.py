
import fsspec
fs = fsspec.filesystem('onedata')
files = fs.ls('/icsa2027_data_20261101T090944Z/s1z')
import re
years = {}
for f in files:
    base = f.split('/')[-1]
    m = re.match(r'sst_(\d{8})\.nc', base)
    if m:
        y = base[4:8]
        years[y] = years.get(y, 0) + 1
print(sorted(years.items()))
print("total files:", len(files))
