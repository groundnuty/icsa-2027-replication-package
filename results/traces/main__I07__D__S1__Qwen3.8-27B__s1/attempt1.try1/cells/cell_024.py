import inspect
from numpy.lib import _function_base_impl as F
src = inspect.getsource(F)
i = src.find("def _compute_virtual_index")
print(src[i:i+1200])
i = src.find("def _quantile_unchecked")
print("==============")
print(src[i:i+4000])
