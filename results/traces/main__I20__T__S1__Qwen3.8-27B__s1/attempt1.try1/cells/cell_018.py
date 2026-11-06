import inspect, re
from numpy.lib._function_base_impl import _quantile
src = inspect.getsource(_quantile)
i = src.find("h = (n")
print(src[max(0,i-3000):i+2000])