
# Find the _quantile function
import numpy as np
from numpy.lib._function_base_impl import _quantile
import inspect
src = inspect.getsource(_quantile)
# Find the hazen part
idx = src.find('hazen')
print(src[max(0,idx-500):idx+500])
