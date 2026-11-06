import inspect
import onedatarestfsspec.core as core
src = inspect.getsource(core)
# find list_children usage
import re
idx = src.find('list_children')
print(src[max(0,idx-2000):idx+3000])
