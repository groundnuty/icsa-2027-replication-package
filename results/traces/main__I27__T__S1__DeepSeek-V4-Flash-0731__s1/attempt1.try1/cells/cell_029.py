
import onedatarestfsspec
import inspect
from onedatarestfsspec.core import OnedataFileSystem

src = inspect.getsource(OnedataFileSystem)
lines = src.split('\n')
# Print lines 220-260
for i in range(200, min(280, len(lines))):
    print(f"{i}: {lines[i]}")
