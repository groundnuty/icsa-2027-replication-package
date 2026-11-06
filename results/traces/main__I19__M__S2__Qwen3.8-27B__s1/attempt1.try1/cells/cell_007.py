import numpy as np, inspect
import numpy.lib._function_base_impl as F
src = inspect.getsource(F._QuantileMethods)
print(src[:6000])
