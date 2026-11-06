import fsspec
fs = fsspec.filesystem('onedata')
print("Files in s1z:", fs.ls('icsa2027_data_20261101T090944Z/s1z')[:10])
print("Files in s2z:", fs.ls('icsa2027_data_20261101T090944Z/s2z')[:10])
