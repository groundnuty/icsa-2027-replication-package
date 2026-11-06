import fsspec
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
files = [f for f in fs.ls(base) if f.endswith('.nc')]
files.sort()
print("count:", len(files))
print("first:", files[0])
print("last:", files[-1])
