import fsspec
fs = fsspec.filesystem('onedata')
base_path = 'icsa2027_data_20261101T090944Z/s1z'
files = fs.ls(base_path)
print(f"Found {len(files)} files")
for f in files[:50]:
    print(f)
