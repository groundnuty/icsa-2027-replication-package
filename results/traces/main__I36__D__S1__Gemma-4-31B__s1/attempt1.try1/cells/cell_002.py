import fsspec
fs = fsspec.filesystem('onedata')
base_path = 'icsa2027_data_20261101T090944Z/s1z'
files = fs.ls(base_path)
print(files[:20]) # Print first 20 files to see the structure
