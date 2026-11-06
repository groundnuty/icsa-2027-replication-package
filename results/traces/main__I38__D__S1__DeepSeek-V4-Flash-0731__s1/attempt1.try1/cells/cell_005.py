import fsspec
fs = fsspec.filesystem('onedata')
# Let's look at the root
print(fs.ls('/'))
