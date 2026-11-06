import fsspec
fs = fsspec.filesystem('onedata')
# List the dataset directory
entries = fs.ls('icsa2027_data_20261101T090944Z/s1z')
for e in entries:
    print(e)
