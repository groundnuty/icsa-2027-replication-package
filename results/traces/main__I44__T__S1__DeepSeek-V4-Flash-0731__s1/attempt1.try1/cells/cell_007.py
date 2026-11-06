import fsspec
fs = fsspec.filesystem('onedata')
files2 = fs.ls('icsa2027_data_20261101T090944Z/s2z')
print(files2)
