import inspect
from numpy.lib import _function_base_impl as fbi
src = inspect.getsource(fbi._quantile_1d)
print(src)
