import fsspec
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s1z'
files = sorted(fs.ls(path))
print(f"First file: {files[0]}")
print(f"Last file: {files[-1]}")
print(f"Total files: {len(files)}")
