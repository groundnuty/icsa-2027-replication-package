import fsspec
import os

fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s1z'
contents = fs.ls(path, detail=False)
dirs = [d for d in contents if fs.isdir(d)]
print(f"Directories in {path}: {dirs}")
