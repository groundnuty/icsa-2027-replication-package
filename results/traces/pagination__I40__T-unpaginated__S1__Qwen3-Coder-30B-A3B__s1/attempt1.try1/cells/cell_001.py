import fsspec
import os

# Set up the filesystem
fs = fsspec.filesystem('onedata')

# List files in the dataset directory
dataset_dir = 'icsa2027_data_20261101T090944Z/s1z'
files = fs.ls(dataset_dir)
print("Available files:")
for f in files:
    print(f)