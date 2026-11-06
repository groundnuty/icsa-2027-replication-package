import fsspec
fs = fsspec.filesystem('onedata')
root_dir = 'icsa2027_data_20261101T090944Z/s1z'
files = fs.ls(root_dir)
print(files[:20]) # Print first 20 files to see the naming convention
