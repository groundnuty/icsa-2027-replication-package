import numpy.lib._function_base_impl as F
import inspect
src = inspect.getsource(F._quantile_unchecked)
print(src[:4000])
