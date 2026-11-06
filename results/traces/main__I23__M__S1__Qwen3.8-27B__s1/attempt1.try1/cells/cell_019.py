import numpy as np, inspect
import numpy.lib._function_base_impl as fb
src = inspect.getsource(fb)
i = src.find("hazen")
print(src[i-2500:i+1500])
