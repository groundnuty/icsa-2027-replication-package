import fsspec
fs = fsspec.filesystem('onedata')
root = 'icsa2027_data_20261101T090944Z/s1z'
try:
    entries = fs.ls(root)
    print(f"All entries in {root}: {entries}")
except Exception as e:
    print(f"Error: {e}")
