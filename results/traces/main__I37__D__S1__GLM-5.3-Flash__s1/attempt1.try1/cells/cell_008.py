import onedatarestfsspec, inspect, pkgutil
import onedatarestfsspec.core as core
src = inspect.getsource(core.OnedataFileSystem.ls)
print(src[:3000])
