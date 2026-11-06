import fsspec, os
fs = fsspec.filesystem('onedata')
# list root
print(fs.ls('/'))
