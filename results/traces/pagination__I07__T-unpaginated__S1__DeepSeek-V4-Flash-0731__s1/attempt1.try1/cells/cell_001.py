
import fsspec
fs = fsspec.filesystem('onedata')
# Explore the dataset directory
path = 'icsa2027_data_20261101T090944Z/s1z'
print(fs.ls(path))
