import numpy
import inspect
src = inspect.getsource(numpy.lib._function_base_impl)
i = src.find('def _quantile')
print(src[i:i+5200])
