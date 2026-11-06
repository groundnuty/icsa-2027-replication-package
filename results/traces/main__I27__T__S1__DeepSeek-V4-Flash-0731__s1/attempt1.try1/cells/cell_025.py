
import onedatarestfsspec
import inspect
from onedatarestfsspec.core import OnedataFileSystem

# Look at _ls_from_cache 
src = inspect.getsource(OnedataFileSystem._ls_from_cache)
print(src)
