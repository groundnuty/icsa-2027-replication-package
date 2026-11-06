
import fsspec
fs = fsspec.filesystem('onedata')
# Explore s2z
files = fs.ls('icsa2027_data_20261101T090944Z/s2z')
print(f"Count: {len(files)}")
for f in files[:10]:
    print(f)
print("...")
for f in files[-10:]:
    print(f)
