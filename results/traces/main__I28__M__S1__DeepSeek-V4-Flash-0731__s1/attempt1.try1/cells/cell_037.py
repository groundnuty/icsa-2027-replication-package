
import numpy as np
from numpy.lib._function_base_impl import _quantile
import inspect
src = inspect.getsource(_quantile)
# Find where methods are handled
print(src[-3000:])
