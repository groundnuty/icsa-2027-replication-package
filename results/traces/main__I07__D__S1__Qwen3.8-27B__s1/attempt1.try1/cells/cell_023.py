import inspect
from numpy.lib import _function_base_impl as F
src = inspect.getsource(F)
i = src.find("def _compute_virtual_index")
print(src[i:i+700])
i = src.find("def _quantile_unchecked")
seg = src[i:i+6000]
j = seg.find("index")
print("---- interpolation part ----")
k = seg.find("index = ")
print(seg[k-200:k+1500])
