import numpy, inspect, os
import numpy.lib.function_base as fb
src = inspect.getsource(fb)
# find the hazen part
i = src.find("hazen")
print(src[i-3000:i+1500])
