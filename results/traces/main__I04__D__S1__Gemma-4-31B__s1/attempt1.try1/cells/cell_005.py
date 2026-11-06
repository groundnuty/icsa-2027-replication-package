import fsspec
fs = fsspec.filesystem('onedata')
base_path = 'icsa2027_data_20261101T090944Z/s2z'
files = fs.ls(base_path)
files.sort()
print(f"First file: {files[0]}")
print(f"Last file: {files[-1]}")
print(f"Total files: {len(files)}")
