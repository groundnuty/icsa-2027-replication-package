
import fsspec
fs = fsspec.filesystem('onedata')
# List the files to understand the date range
files = fs.ls('icsa2027_data_20261101T090944Z/s1z')
print(f"Total files: {len(files)}")
# Get the first and last few files
print(files[:5])
print(files[-5:])
