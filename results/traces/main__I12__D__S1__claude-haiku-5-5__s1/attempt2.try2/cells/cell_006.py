import fsspec
fs = fsspec.filesystem('onedata')
base='icsa2027_data_20261101T090944Z/s1z/'
for d in ['19911227','19920101','20021231','20030105','20090601','20090831','19840927']:
    print(d, fs.exists(base+f'sst_{d}.nc'))
print(fs.ls(base, detail=False)[-3:])