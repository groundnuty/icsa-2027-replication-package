import numpy, inspect
src = inspect.getsource(numpy.lib._function_base_impl)
k = src.find('def _compute_virtual_index')
print(src[k:k+700])
