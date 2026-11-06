import inspect
import numpy.lib._function_base_impl as fb
s = inspect.getsource(fb)
i = s.find("def _quantile_ureduce_func")
print(s[i:i+3500])
