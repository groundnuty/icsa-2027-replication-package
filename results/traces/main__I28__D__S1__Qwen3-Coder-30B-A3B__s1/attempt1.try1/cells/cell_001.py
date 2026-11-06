import fsspec
fs = fsspec.filesystem('onedata')
print("Dataset directory contents:")
contents = fs.ls('/icsa2027_data_20261101T090944Z/s1z')
print(f"Number of files: {len(contents)}")
print("First few files:")
for i, file in enumerate(contents[:5]):
    print(f"  {file}")