import fsspec
fs = fsspec.filesystem('onedata')
print("Files in directory:")
files = fs.ls('/icsa2027_data_20261101T090944Z/s1z')
print(f"Total files: {len(files)}")
print("First 5 files:", files[:5])