import fsspec
import os

fs = fsspec.filesystem('onedata')
base_dir = 'icsa2027_data_20261101T090944Z/s1z'
files = fs.ls(base_dir)
print(files)
