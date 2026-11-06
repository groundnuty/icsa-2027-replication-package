
import fsspec
fs = fsspec.filesystem('onedata')
# List the top level
print(fs.ls('icsa2027_data_20261101T090944Z'))
