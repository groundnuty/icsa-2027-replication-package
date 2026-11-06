
import time
time.sleep(5)
import fsspec
fs = fsspec.filesystem('onedata')
try:
    files = fs.ls('icsa2027_data_20261101T090944Z/s1z')
    print(f"Connection OK, {len(files)} files")
except Exception as e:
    print(f"Connection error: {e}")
