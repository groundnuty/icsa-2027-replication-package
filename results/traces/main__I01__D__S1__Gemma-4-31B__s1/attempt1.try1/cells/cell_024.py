import fsspec
fs = fsspec.filesystem('onedata')
try:
    print(fs.ls('/'))
except Exception as e:
    print(f"Error: {e}")
