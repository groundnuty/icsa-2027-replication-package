import fsspec
import os

fs = fsspec.filesystem('onedata')
# Try to find any file that has 'sst' in its name anywhere in the system
all_files = fs.find('icsa2027_data_20261101T090944Z')
print(f"Total files found: {len(all_files)}")
# Check for any file containing '2008' or '1992' in its path
filtered = [f for f in all_files if '2008' in f or '1992' in f]
print(f"Filtered files count: {len(filtered)}")
if filtered:
    print(filtered[:10])
