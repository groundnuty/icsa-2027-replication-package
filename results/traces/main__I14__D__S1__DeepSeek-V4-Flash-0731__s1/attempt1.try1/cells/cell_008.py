
import fsspec
fs = fsspec.filesystem('onedata')

# Get the full list without truncation
files = fs.ls('icsa2027_data_20261101T090944Z/s1z')
print(f"Total files in s1z: {len(files)}")

# Print all file names in chunks to avoid truncation
for i in range(0, min(len(files), 100), 10):
    print(files[i:i+10])
