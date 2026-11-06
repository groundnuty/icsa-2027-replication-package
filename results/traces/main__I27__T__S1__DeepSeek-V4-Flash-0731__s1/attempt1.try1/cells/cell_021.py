
import fsspec
fs = fsspec.filesystem('onedata')
# Let's look at the internal _ls method
import inspect
# Check what the actual filesystem class has
print(type(fs))
# Let's look at the base class
from fsspec.spec import AbstractFileSystem
print(inspect.getsource(AbstractFileSystem.ls))
