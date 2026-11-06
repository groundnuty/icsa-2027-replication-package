
import numpy.lib._function_base_impl as fb
import inspect, re
src = inspect.getsource(fb)
i = src.find('def _compute_virtual_index')
print(src[i:i+800])
