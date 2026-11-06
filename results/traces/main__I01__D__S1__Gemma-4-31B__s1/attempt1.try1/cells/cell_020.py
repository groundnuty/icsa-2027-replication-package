import fsspec
fs = fsspec.filesystem('onedata')
root = 'icsa2027_data_20261101T090944Z'
all_contents = fs.ls(root)
print(f"Contents of {root}:")
for item in all_contents:
    print(item)
