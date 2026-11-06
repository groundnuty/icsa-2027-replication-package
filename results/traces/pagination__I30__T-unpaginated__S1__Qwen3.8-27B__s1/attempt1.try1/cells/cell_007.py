
import numpy, inspect, re
src = inspect.getsource(numpy.lib._methods)
i = src.find('hazen')
print(src[max(0,i-3000):i+2000])
