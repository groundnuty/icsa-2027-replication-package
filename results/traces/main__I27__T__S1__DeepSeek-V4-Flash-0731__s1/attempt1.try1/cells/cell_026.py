
import onedatarestfsspec
import inspect
from onedatarestfsspec.core import OnedataFileSystem

# Look at all methods that might do listing
for name in dir(OnedataFileSystem):
    if name.startswith('_') and ('list' in name.lower() or 'ls' in name.lower() or 'child' in name.lower()):
        print(name)
