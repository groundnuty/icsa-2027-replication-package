import fsspec
fs = fsspec.filesystem('onedata')
root_path = 'icsa2027_data_20261101T090944Z'
# List only the first level of directories
dirs = [d for d in fs.ls(root_path) if fs.isdir(d)]
print(dirs)
