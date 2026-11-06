import fsspec
fs = fsspec.filesystem('onedata')
base_path = 'icsa2027_data_20261101T090944Z'
try:
    files = fs.ls(base_path)
    print(f"Contents of {base_path}: {files}")
except Exception as e:
    print(f"Error: {e}")
