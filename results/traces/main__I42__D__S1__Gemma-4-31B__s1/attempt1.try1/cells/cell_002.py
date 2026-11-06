import fsspec
fs = fsspec.filesystem('onedata')
root_parent = 'icsa2027_data_20261101T090944Z'
try:
    files = fs.ls(root_parent)
    print(f"Files in {root_parent}:")
    for f in files:
        print(f)
except Exception as e:
    print(f"Error listing {root_parent}: {e}")
