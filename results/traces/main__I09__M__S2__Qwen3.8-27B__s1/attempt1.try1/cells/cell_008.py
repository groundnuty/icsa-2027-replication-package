import inspect
from numpy.lib import _function_base_impl as fb
src = inspect.getsource(fb._quantile_ureduce_func)
print(src[:6000])