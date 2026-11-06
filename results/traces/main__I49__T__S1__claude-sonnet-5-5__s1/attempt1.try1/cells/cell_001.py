import fsspec
fs=fsspec.filesystem('onedata')
p='icsa2027_data_20261101T090944Z/s1z'
for x in fs.ls(p,detail=False)[:50]:print(x)