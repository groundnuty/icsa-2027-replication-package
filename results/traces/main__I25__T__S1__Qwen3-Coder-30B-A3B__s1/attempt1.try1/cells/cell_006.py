# Check if we have a different pattern for files
import fsspec
import re
from datetime import datetime

fs = fsspec.filesystem('onedata')
all_files = fs.ls('/icsa2027_data_20261101T090944Z/s1z')

# Look for patterns that might indicate different datasets or versions
print("All files:")
for f in all_files[:20]:  # Show first 20
    print(f)

# Check if there are other directories or files that might contain the required data
print("\nChecking for other possible datasets...")
try:
    root_files = fs.ls('/icsa2027_data_20261101T090944Z')
    print("Root directory contents:")
    for item in root_files:
        print(item)
except Exception as e:
    print(f"Error accessing root: {e}")