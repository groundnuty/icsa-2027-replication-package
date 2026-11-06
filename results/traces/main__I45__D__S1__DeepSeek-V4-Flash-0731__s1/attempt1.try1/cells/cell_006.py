
import fsspec
fs = fsspec.filesystem('onedata')
# Look at what's at the root
print(fs.ls('/'))
