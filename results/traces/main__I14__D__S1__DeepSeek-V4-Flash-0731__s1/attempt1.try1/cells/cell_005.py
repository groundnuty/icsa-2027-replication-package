
import fsspec
fs = fsspec.filesystem('onedata')

# Check s2z
files2 = fs.ls('icsa2027_data_20261101T090944Z/s2z')
print(f"Files in s2z: {len(files2)}")
if files2:
    print(f"First: {files2[0]}")
    print(f"Last: {files2[-1]}")
