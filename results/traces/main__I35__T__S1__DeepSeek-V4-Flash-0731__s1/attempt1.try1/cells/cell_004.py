
import fsspec
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
files = fs.ls(base)
print(len(files))
# print all unique years properly
import re
years = set()
for f in files:
    m = re.search(r'sst_(\d{4})', f)
    if m:
        years.add(m.group(1))
print(sorted(years))
