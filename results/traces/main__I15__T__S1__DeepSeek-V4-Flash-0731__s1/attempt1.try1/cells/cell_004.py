import fsspec
fs = fsspec.filesystem('onedata')
# Check the parent directory
print(fs.ls('icsa2027_data_20261101T090944Z'))
