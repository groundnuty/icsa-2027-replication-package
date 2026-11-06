
import onedatarestfsspec
import inspect
# Find the actual implementation
from onedatarestfsspec.core import OnedataFileSystem

# Find the _ls or similar method
for name in dir(OnedataFileSystem):
    if 'ls' in name.lower() or 'list' in name.lower():
        print(name)
