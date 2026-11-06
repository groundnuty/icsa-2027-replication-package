import fsspec
import os

fs = fsspec.filesystem('onedata')
root = 'icsa2027_data_20261101T090944Z'
all_files = fs.find(root)
print(f"Total files: {len(all_files)}")
# Print the first 500 filenames to see if there's a pattern I missed
for i, f in enumerate(all_files):
    if i < 500:
        print(f)
    else:
        break
