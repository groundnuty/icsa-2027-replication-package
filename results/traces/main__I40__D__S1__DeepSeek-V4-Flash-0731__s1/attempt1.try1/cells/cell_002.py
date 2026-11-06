
import fsspec
fs = fsspec.filesystem('onedata')
files = fs.ls('icsa2027_data_20261101T090944Z/s1z')
print(f"Total files: {len(files)}")
# Show first few and last few
for f in files[:5]:
    print(f)
print("...")
for f in files[-5:]:
    print(f)
