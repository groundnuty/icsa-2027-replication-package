import numpy as np, inspect, re
from numpy._core import _methods
src = inspect.getsource(_methods)
# find hafn quantile implementation
i = src.find('def _quantile_hafn')
print(src[i:i+2600] if i>=0 else 'not in _methods')
