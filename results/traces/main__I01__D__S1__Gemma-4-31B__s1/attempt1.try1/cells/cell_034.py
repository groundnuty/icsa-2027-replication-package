import fsspec
import os

fs = fsspec.filesystem('onedata')
root = 'icsa2027_data_20261101T090944Z'
all_files = fs.find(root)
# Print unique folders
folders = set([os.path.dirname(f) for f in all_files])
print(f"Unique folders: {sorted(list(folders))}")
