import fsspec
fs = fsspec.filesystem('onedata')
root_dir = 'icsa2027_data_20261101T090944Z/s1z'
# Try to list files with a different method if possible, or check for subdirs
print(fs.ls(root_dir, detail=False))
