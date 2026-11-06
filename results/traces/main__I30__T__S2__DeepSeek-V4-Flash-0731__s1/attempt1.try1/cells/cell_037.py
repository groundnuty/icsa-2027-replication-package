
import numpy as np
from numpy.lib._function_base_impl import _QuantileMethods

# Get the hazen method
hazen = _QuantileMethods['hazen']
print("hazen:", hazen)
print("get_virtual_index:", hazen['get_virtual_index'])
print("fix_gamma:", hazen['fix_gamma'])

# Test with values_count=5, quantiles=[0.9]
print(hazen['get_virtual_index'](5, np.array([0.9])))
print(hazen['get_virtual_index'](10, np.array([0.9])))
print(hazen['get_virtual_index'](4, np.array([0.25])))
