import fsspec
fs = fsspec.filesystem('onedata')
contents = fs.ls('/icsa2027_data_20261101T090944Z/s1z')
print("Contents of the directory:")
for item in contents:
    print(item)