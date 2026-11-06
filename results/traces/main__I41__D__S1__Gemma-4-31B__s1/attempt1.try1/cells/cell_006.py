import fsspec

fs = fsspec.filesystem('onedata')
remote_dir = 'icsa2027_data_20261101T090944Z/s1z'
files = fs.ls(remote_dir)
print(f"Total files: {len(files)}")
# Print a sample of files to see patterns
for f in files[:50]:
    print(f)
