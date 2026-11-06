import fsspec
fs = fsspec.filesystem('onedata')
entries = fs.ls('icsa2027_data_20261101T090944Z/s1z', detail=True)
names = sorted(e['name'] for e in entries)
print(names[0], names[-1], len(names))
# check all match pattern
import re
bad = [n for n in names if not re.fullmatch(r'sst_\d{8}\.nc', n)]
print('bad:', bad[:10], len(bad))
dates = sorted(n[4:12] for n in names)
print(dates[0], dates[-1])
# check presence of files we need
need = ['19911227','19911231','19920229','19930228','20030105','20100601','20100831','20100531','20100901']
for d in need:
    print(d, f'sst_{d}.nc' in set(names))
