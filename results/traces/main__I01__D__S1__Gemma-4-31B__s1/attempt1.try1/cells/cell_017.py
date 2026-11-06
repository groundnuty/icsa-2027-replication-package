import fsspec
import os

fs = fsspec.filesystem('onedata')
root = 'icsa2027_data_20261101T090944Z'
# Try to find any file that contains '2008' in its filename (not path)
all_files = fs.find(root)
found_2008 = [f for f in all_files if '2008' in os.path.basename(f)]
print(f"Files with 2008 in basename: {len(found_2008)}")
if found_2008:
    print(found_2008[:10])

found_1992 = [f for f in all_files if '1992' in os.path.basename(f)]
print(f"Files with 1992 in basename: {len(found_1992)}")
if found_1992:
    print(found_1992[:10])
