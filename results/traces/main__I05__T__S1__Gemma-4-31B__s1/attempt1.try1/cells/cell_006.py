import fsspec
fs = fsspec.filesystem('onedata')
root_dir = 'icsa2027_data_20261101T090944Z/s1z'
all_files = fs.ls(root_dir)
print(f"Total files: {len(all_files)}")
print(f"First file: {all_files[0]}")
print(f"Last file: {all_files[-1]}")
