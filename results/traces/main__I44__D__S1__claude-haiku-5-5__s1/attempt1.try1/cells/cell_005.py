import fsspec
fs = fsspec.filesystem('onedata')
base='icsa2027_data_20261101T090944Z/s1z'
for d in ['19911227','19920101','20040601','20040831','20030105']:
    print(d, fs.exists(f'{base}/sst_{d}.nc'))
allf=fs.ls(base, detail=False)
print(len(allf), allf[-2:])