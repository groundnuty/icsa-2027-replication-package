import fsspec
fs = fsspec.filesystem('onedata')
root = 'icsa2027_data_20261101T090944Z'
print(fs.ls(root))
# Let me try to list everything in the root directory recursively if possible.
# Or just check for any other folders.
