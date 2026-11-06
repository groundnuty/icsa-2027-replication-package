import inspect
import numpy.lib._function_base_impl as fb
s = inspect.getsource(fb)
i = s.find("methods = {")
print(s[i:i+2600])
