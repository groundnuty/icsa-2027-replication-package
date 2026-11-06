
import fsspec
fs = fsspec.filesystem('onedata')
# Check s2z
files2 = fs.ls('icsa2027_data_20261101T090944Z/s2z')
print(len(files2))
print(files2[:5])
print(files2[-5:])
import re
years = set()
for f in files2:
    m = re.search(r'sst_(\d{4})', f)
    if m:
        years.add(m.group(1))
print(sorted(years))
