import numpy as np, inspect
import numpy.lib._function_base_impl as fb
src = inspect.getsource(fb._nanquantile)
print(src[:4000])
