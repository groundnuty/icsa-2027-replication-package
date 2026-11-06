import fsspec
import os

# Create the filesystem
fs = fsspec.filesystem('onedata')

# List the directory to understand the structure
try:
    files = fs.ls('/icsa2027_data_20261101T090944Z/')
    print("Files in root directory:")
    for f in files:
        print(f)
except Exception as e:
    print(f"Error listing root directory: {e}")

# Try to access the specific file
try:
    file_path = '/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
    if fs.exists(file_path):
        print("File exists")
        # Get file info
        file_info = fs.info(file_path)
        print(f"File size: {file_info['size']}")
    else:
        print("File does not exist")
except Exception as e:
    print(f"Error accessing file: {e}")