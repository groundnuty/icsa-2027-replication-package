import fsspec
import os

fs = fsspec.filesystem('onedata')
all_files = fs.find('')
# Search for any file that contains '2008' in its name or path
found_2008 = [f for f in all_files if '2008' in f]
print(f"Found {len(found_2008)} files with '2008' in path/name.")
if found_2008:
    print(found_2008[:10])

found_1992 = [f for f in all_files if '1992' in f]
print(f"Found {len(found_1992)} files with '1992' in path/name.")
if found_1992:
    print(found_1992[:10])
