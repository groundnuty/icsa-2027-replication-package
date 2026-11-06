import onedatarestfsspec.core as core, inspect
# find OnedataFileRESTClient class
obj = core
cands = [n for n in dir(obj) if 'REST' in n or 'Client' in n]
print(cands)
from onedatarestfsspec.core import OnedataFileRESTClient
import inspect
sig = inspect.signature(OnedataFileRESTClient.list_children)
print(sig)
src = inspect.getsource(OnedataFileRESTClient.list_children)
print(src[:3000])
