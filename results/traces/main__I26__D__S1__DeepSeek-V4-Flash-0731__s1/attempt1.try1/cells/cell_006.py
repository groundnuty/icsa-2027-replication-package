import fsspec
fs = fsspec.filesystem('onedata')
# Check s2z
files2 = fs.ls('icsa2027_data_20261101T090944Z/s2z')
print(len(files2))
from collections import Counter
years2 = Counter()
for f in files2:
    name = f.split('/')[-1]
    year = name[4:8]
    years2[year] += 1
print(dict(sorted(years2.items())))
