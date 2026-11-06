import fsspec
fs = fsspec.filesystem('onedata')
files = fs.ls('icsa2027_data_20261101T090944Z/s1z')
# count per year
from collections import Counter
years = Counter()
for f in files:
    name = f.split('/')[-1]
    year = name[4:8]
    years[year] += 1
print(dict(sorted(years.items())))
