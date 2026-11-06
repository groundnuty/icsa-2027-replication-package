import fsspec

fs = fsspec.filesystem('onedata')
root_dir = 'icsa2027_data_20261101T090944Z'
try:
    contents = fs.ls(root_dir)
    print(contents)
except Exception as e:
    print(f"Error: {e}")
