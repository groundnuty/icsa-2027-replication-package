import fsspec
fs = fsspec.filesystem('onedata')
files = fs.ls('/icsa2027_data_20261101T090944Z/s1z/')
print("Total files:", len(files))
print("Sample files:")
for i, f in enumerate(files[:10]):
    print(f)