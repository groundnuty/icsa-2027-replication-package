import numpy, inspect
src = inspect.getsource(numpy.lib._function_base_impl)
k = src.find('_QuantileMethods =')
if k == -1:
    k = src.find('class _QuantileMethod')
print(src[k:k+2500])
