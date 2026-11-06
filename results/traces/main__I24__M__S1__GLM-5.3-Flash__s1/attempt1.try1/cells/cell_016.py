import numpy as np, inspect
import numpy.lib._function_base_impl as fb
src = inspect.getsource(fb._quantile)
print(src[:7000])
