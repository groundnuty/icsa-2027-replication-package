
import fsspec
fs = fsspec.filesystem('onedata')
# Check root
print(fs.ls('/'))
