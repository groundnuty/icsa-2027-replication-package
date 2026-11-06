import numpy as np
from numpy.lib import _function_base_impl as F
f = F._compute_virtual_index
print("hazen(121,0.9):", f(121, np.float64(0.9), 0.5, 0.5))
print("weibull(121,0.9):", f(121, np.float64(0.9), 0, 0))
print("linear(121,0.9):", f(121, np.float64(0.9), 1, 1))
import inspect
try:
    print(inspect.getsource(F._compute_virtual_index))
except Exception as e:
    print(e)
    print(F._compute_virtual_index)