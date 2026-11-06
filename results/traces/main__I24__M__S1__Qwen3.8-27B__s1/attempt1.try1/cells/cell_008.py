import numpy, inspect, os
print(numpy.__version__)
src = inspect.getsourcefile(numpy.quantile)
print(src)
import numpy.lib._function_base_impl as fb
s = inspect.getsource(fb)
import re
i = s.find("def _quantile_unchecked")
print(s[i:i+4000])
