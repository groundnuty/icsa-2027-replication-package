import onedatarestfsspec.core as core, inspect, re
# inspect the underlying REST client's list_children
from onedatarestfsspec import utils
import onedatarestfsspec as pkg
# find OnedataFileRESTClient
import importlib, pkgutil
print([m.name for m in pkgutil.iter_modules(pkg.__path__)])
