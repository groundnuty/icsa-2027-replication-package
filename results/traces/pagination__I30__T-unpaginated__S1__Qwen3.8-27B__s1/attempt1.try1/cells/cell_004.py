
import fsspec
from collections import Counter
fs = fsspec.filesystem('onedata')
names = [p.split('/')[-1] for p in fs.ls('/icsa2027_data_20261101T090944Z/s1z')]
print('total files:', len(names))
years = Counter(n[4:8] for n in names if n.startswith('sst_'))
print(sorted(years.items()))
