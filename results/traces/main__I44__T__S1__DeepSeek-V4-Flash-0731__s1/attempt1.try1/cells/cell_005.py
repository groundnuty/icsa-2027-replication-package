import fsspec
fs = fsspec.filesystem('onedata')
# List the root
print(fs.ls('/'))
# Check the parent directory
print(fs.ls('icsa2027_data_20261101T090944Z'))
