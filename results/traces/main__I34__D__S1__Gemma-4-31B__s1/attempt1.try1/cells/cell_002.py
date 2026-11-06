import fsspec
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s1z'
files = fs.ls(path)
# Print first 20 files to see the naming convention
for f in files[:20]:
    print(f)
