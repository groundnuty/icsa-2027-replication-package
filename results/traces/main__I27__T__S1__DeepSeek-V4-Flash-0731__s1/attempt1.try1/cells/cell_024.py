
import onedatarestfsspec
import inspect
from onedatarestfsspec.core import OnedataFileSystem

# Look at listdir
src = inspect.getsource(OnedataFileSystem.listdir)
print(src)
