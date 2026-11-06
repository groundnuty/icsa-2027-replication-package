import fsspec
import os

fs = fsspec.filesystem('onedata')
root_dir = 'icsa2027_data_20261101T090944Z/s1z'
files = fs.ls(root_dir)
print(files)
