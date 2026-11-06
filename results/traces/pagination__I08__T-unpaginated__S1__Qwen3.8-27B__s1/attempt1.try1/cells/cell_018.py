
import numpy as np
print(np.quantile.__module__)
import numpy.lib._function_base_impl as fb
import inspect, re
src = inspect.getsource(fb)
for m in list(re.finditer(r"method|c1|hazen", src))[:5]:
    pass
i = src.find('hazen')
print(src[i-3000:i+2000])
