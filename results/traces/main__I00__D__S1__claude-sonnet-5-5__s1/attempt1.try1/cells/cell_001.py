import fsspec
fs=fsspec.filesystem('onedata')
p='icsa2027_data_20261101T090944Z/s1z'
for f in fs.ls(p,detail=False)[:50]:print(f, fs.info(f).get('size'))