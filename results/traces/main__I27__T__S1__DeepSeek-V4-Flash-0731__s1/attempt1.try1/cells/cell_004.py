
import fsspec
fs = fsspec.filesystem('onedata')
# Check if there are more directories
print(fs.ls('icsa2027_data_20261101T090944Z'))
