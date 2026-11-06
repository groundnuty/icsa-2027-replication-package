import fsspec
fs = fsspec.filesystem('onedata')
p = 'icsa2027_data_20261101T090944Z/s1z'
files = fs.ls(p, detail=False)
print('count', len(files))
print(files[0], files[-1])
# try glob
g = fs.glob(p + '/sst_*.nc')
print('glob count', len(g))
