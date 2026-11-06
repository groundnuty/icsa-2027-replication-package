import inspect, numpy as np
from numpy.lib import _function_base_impl as fb
src = inspect.getsource(fb._quantile_unchecked)
print(src[:3000])