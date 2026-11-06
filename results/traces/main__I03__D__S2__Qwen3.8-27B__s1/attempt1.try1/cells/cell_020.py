import numpy, inspect
src = inspect.getsource(numpy.lib._function_base_impl)
k = src.find('def _compute_virtual_index')
end = src.find('\n\n', k)
print(src[k:end])
