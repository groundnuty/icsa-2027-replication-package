import fsspec
fs = fsspec.filesystem('onedata')
root_path = 'icsa2027_data_20261101T090944Z'
all_files = fs.find(root_path)
# Print only the first 100 files to avoid overflow
print(all_files[:100])
