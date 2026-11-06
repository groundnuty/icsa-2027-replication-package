import fsspec
fs=fsspec.filesystem('onedata')
p='icsa2027_data_20261101T090944Z/s1z'
print(fs.ls(p)[:50])