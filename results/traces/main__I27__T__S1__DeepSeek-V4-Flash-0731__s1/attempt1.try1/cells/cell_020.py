
import fsspec
fs = fsspec.filesystem('onedata')
# Let's look at the internal implementation
import inspect
src = inspect.getsource(fs.ls)
print(src)
