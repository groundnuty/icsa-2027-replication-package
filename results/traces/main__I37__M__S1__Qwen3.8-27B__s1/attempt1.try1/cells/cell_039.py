import inspect
from numpy.lib import _function_base_impl as fb
src = inspect.getsource(fb)
j = src.find("def _compute_virtual_index")
print(src[j:j+1800])
