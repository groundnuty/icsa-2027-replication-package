
import fsspec
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
files = fs.ls(base)
print(len(files))
print(files[:5])
print(files[-5:])
# Check unique years
import re
years = set()
for f in files:
    m = re.search(r'sst_(\d{4})(\d{2})(\d{2})\.nc', f.split('/')[-1])
    if m:
        years.add(m.group(1))
print(sorted(years))
