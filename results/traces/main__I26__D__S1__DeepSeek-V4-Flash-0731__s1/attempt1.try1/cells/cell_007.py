import fsspec
fs = fsspec.filesystem('onedata')
# Check s2z contents
print(fs.ls('icsa2027_data_20261101T090944Z/s2z'))
