import fsspec
fs = fsspec.filesystem('onedata')
# Explore s2z
files2 = fs.ls('icsa2027_data_20261101T090944Z/s2z')
print(len(files2))
print(files2[:5])
print(files2[-5:])
import re
years = set()
for f in files2:
    name = f.split('/')[-1]
    m = re.match(r'sst_(\d{8})\.nc', name)
    if m:
        years.add(m.group(1)[:4])
print(sorted(years))
