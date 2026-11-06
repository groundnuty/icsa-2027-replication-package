
import numpy, inspect
import numpy.lib._nanfunctions_impl as nf
src = inspect.getsource(nf)
i = src.find('def _quantile_')
print(src[i:i+5000])
