import numpy, inspect
src = inspect.getsource(numpy.lib._function_base_impl)
i = src.find('def _quantile(')
j = src.find('def percentile', i)
seg = src[i:j]
# print the core computation part
k = seg.find('q = np.asarray')
print(seg[k:k+4200])
