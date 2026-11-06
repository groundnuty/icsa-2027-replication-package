import fsspec
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
paths = fs.ls(base)
print(len(paths))
for p in paths[:50]:
    print(p)
