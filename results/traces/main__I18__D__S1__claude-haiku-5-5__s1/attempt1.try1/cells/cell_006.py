import fsspec
fs = fsspec.filesystem('onedata')
base='icsa2027_data_20261101T090944Z/s1z/'
for d in ['19911227','19920101','19950601','20030105','20100601','20100831']:
    print(d, fs.exists(base+f'sst_{d}.nc'))
print(fs.ls('icsa2027_data_20261101T090944Z', detail=False))
print(fs.ls('icsa2027_data_20261101T090944Z/s1z', detail=False)[-3:])