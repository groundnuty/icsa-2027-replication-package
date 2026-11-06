import numpy, inspect, re
from numpy.lib import _function_base_impl as fb
src = inspect.getsource(fb)
i = src.find("'hazen': {")
print(src[i-200:i+400])
print("==========")
j = src.find("def _get_virtual_index")
if j < 0:
    j = src.find("_get_virtual_index")
print(src[j-200:j+2200])
