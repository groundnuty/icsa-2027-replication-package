
import fsspec
fs = fsspec.filesystem('onedata')
# Let's look at the OnedataFileSystem class directly
import onedatarestfsspec
import inspect
# Get the class
from onedatarestfsspec.core import OnedataFileSystem
# Check ls method
src = inspect.getsource(OnedataFileSystem.ls)
print(src)
