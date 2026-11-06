
import fsspec
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
# List all files
files = fs.ls(base)
print(f"Total files: {len(files)}")
print("First few:", files[:5])
print("Last few:", files[-5:])
