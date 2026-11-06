
import fsspec
fs = fsspec.filesystem('onedata')
paths = fs.ls('/icsa2027_data_20261101T090944Z/s1z')
print(paths)
