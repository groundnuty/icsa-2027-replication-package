import fsspec
fs = fsspec.filesystem('onedata')
# List the files to understand the range of years available
files = fs.ls('icsa2027_data_20261101T090944Z/s1z')
print(len(files))
print(files[:5])
print(files[-5:])
