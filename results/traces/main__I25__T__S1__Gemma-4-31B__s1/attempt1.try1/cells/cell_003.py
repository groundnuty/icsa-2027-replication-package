import fsspec
fs = fsspec.filesystem('onedata')
root_path = 'icsa2027_data_20261101T090944Z'
print(fs.ls(root_path))
