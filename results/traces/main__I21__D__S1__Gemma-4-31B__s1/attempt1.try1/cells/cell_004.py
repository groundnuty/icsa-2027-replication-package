import fsspec

fs = fsspec.filesystem('onedata')
root_dir = 'icsa2027_data_20261101T090944Z'
files = fs.ls(root_dir)
print(files)
