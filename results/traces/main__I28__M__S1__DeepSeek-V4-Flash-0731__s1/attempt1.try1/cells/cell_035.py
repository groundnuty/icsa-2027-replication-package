
# Let me find the numpy source for the hazen method
import numpy as np
import inspect

# Check where the method is implemented
from numpy.lib._function_base_impl import _quantile_ureduce_func
print(inspect.getsource(_quantile_ureduce_func)[:3000])
