import fsspec
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s1z'
files = fs.ls(path)
print(f"Total files in {path}: {len(files)}")
print(files[:100])
