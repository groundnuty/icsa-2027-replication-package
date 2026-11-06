
import onedatarestfsspec
import inspect
from onedatarestfsspec.core import OnedataFileSystem

# Look for how it does the actual listing - specifically the `ls` or `_ls` method
# Let's look at where the client's list_children is used
src = inspect.getsource(OnedataFileSystem)
# Find the _ls or listing related method
import re
# Look for methods that reference list_children
lines = src.split('\n')
for i, line in enumerate(lines):
    if 'list_children' in line or '_ls' in line:
        print(f"{i}: {line}")
