import numpy, inspect, re
from numpy.lib import _nanfunctions_impl
src = inspect.getsource(_nanfunctions_impl)
i = src.find('def _quantile_ureduce')
print(src[i:i+2500])
