import numpy as np, inspect, re
import numpy.lib._function_base as fb
src = inspect.getsource(fb)
i = src.find("def _quantile_unchecked")
print(src[i:i+4000])
