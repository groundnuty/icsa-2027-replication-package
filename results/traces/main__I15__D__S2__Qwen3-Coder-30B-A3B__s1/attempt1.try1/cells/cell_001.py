import fsspec
import os

# Create the filesystem
fs = fsspec.filesystem('onedata')

# List the directory structure to find the correct path
try:
    files = fs.ls('/icsa2027_data_20261101T090944Z/')
    print("Files in root directory:")
    for f in files:
        print(f)
except Exception as e:
    print(f"Error listing root directory: {e}")

# Try to list the s2z directory
try:
    files = fs.ls('/icsa2027_data_20261101T090944Z/s2z/')
    print("\nFiles in s2z directory:")
    for f in files:
        print(f)
except Exception as e:
    print(f"Error listing s2z directory: {e}")