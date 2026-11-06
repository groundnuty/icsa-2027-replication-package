import numpy as np
from numpy.lib import _function_base
print([n for n in dir(_function_base) if 'quant' in n.lower()])
import inspect
src = inspect.getsource(_function_base)
i = src.find('def _quantile_hafn')
print(src[i:i+2000] if i>=0 else 'no _quantile_hafn in _function_base')
