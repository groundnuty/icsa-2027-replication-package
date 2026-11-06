
import fsspec
fs = fsspec.filesystem('onedata')
# List top-level
print(fs.ls('/'))
