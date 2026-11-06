
import fsspec
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s1z'
files = fs.ls(path)
print(len(files))
# Show first and last few
for f in files[:5]:
    print(f)
print('...')
for f in files[-5:]:
    print(f)
