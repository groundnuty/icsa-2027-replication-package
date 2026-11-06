
import onedatarestfsspec
import inspect
from onedatarestfsspec.core import OnedataFileSystem

# Look for how it does the actual listing - maybe it's in a helper
# Let's look at the whole class
src = inspect.getsource(OnedataFileSystem)
print(src[:5000])
