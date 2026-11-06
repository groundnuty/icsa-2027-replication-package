
import fsspec
fs = fsspec.filesystem('onedata')
# Check what methods the filesystem supports
print(type(fs))
# Let's look at the filesystem's API
print([m for m in dir(fs) if not m.startswith('_')])
