import numpy, inspect
src = inspect.getsource(numpy.lib._function_base_impl)
i = src.find('def _quantile(')
j = src.find('def percentile', i)
seg = src[i:j]
# strip docstring
start = seg.find('"""', 3)
end = seg.find('"""', start+3) + 3
print(seg[end:end+4000])
