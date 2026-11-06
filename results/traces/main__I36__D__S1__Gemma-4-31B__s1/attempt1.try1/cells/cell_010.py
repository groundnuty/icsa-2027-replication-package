import fsspec
fs = fsspec.filesystem('onedata')
base_path = 'icsa2027_data_20261101T090944Z/s2z'
all_files = fs.ls(base_path)
print(all_files[:20])
