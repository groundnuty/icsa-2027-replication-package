
import numpy as np
import inspect
from numpy.lib._function_base_impl import _QuantileMethods

# Get the lambda source
hazen = _QuantileMethods['hazen']
print(hazen['get_virtual_index'])
print(inspect.getsource(hazen['get_virtual_index']))
print()
print(hazen['fix_gamma'])
print(inspect.getsource(hazen['fix_gamma']))
