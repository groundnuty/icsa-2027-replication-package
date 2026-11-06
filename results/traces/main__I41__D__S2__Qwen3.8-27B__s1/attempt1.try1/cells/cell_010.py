import numpy as np, inspect
import numpy.lib._function_base_impl as fb
src = inspect.getsource(fb)
i = src.find('def _quantile_hafn')
print(src[i:i+1800] if i>=0 else 'not found')
