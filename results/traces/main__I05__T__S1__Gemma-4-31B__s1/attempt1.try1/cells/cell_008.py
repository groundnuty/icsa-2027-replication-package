import fsspec
fs = fsspec.filesystem('onedata')
parent_dir = 'icsa2027_data_20261101T090944Z'
print(fs.ls(parent_dir))
