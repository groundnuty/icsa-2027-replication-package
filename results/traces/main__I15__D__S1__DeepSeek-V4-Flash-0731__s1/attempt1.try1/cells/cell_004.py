
import fsspec
fs = fsspec.filesystem('onedata')
# Explore the parent directory structure
print(fs.ls('icsa2027_data_20261101T090944Z'))
