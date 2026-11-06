import fsspec
fs = fsspec.filesystem('onedata')
entries = fs.ls('icsa2027_data_20261101T090944Z/s1z', detail=True)
names = set(e['name'] for e in entries)
need = ['19911227','19911231','19920229','19930228','20030105','20100601','20100831','20100531','20100901','20021231','19920101']
for d in need:
    print(d, f'sst_{d}.nc' in names)
print(len(names))
