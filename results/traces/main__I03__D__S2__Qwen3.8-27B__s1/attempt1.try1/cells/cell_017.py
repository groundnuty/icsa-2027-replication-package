import numpy, inspect
src = inspect.getsource(numpy.lib._function_base_impl)
i = src.find('_QuantileMethods')
# print class definition
k = src.find('class _QuantileMethods')
if k == -1:
    k = src.find('class _QuantileMethod')
print(src[k:k+3500])
for fn in ['def _get_indexes', 'def _get_gamma', 'def _lerp']:
    m = src.find(fn)
    print("=====", fn)
    print(src[m:m+900])
