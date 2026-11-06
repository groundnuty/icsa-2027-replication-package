
import fsspec
fs = fsspec.filesystem('onedata')
# List all files to understand the date range
files = fs.ls('icsa2027_data_20261101T090944Z/s1z')
print(len(files))
print(files[0])
print(files[-1])
