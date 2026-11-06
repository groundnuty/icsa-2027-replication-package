import numpy, inspect
from numpy.lib import _function_base_impl as F
src = inspect.getsource(F)
i = src.find("hazen")
print(src[i-3000:i+800])
