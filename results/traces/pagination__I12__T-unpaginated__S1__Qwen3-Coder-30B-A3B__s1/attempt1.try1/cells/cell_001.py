import fsspec
fs = fsspec.filesystem('onedata')
files = fs.ls('/icsa2027_data_20261101T090944Z/s1z')
print("Files in directory:")
for f in files:
    print(f)