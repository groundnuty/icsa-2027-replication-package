
import fsspec
fs = fsspec.filesystem('onedata')
# Explore s2z
files2 = fs.ls('icsa2027_data_20261101T090944Z/s2z')
print(f"Files in s2z: {len(files2)}")
for f in files2[:5]:
    print(f)
print("...")
for f in files2[-5:]:
    print(f)
