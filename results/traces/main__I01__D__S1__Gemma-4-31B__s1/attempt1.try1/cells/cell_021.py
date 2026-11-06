import fsspec
import os

fs = fsspec.filesystem('onedata')
all_files = fs.find('') # Search everything (might be too slow, but let's try)
# To avoid too many files, let's just look for paths containing '2008'
found_2008 = [f for f in all_files if '2008' in f]
print(f"Found {len(found_2008)} files with '2008' in the path.")
if found_2008:
    print(found_2008[:10])
