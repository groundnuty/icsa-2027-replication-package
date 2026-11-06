
import fsspec
fs = fsspec.filesystem('onedata')
# Explore root
print(fs.ls(''))
