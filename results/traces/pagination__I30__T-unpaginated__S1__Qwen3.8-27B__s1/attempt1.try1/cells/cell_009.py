
import numpy, inspect
from numpy.lib import _function_base_impl as fb
src = inspect.getsource(fb)
i = src.find("'hazen'")
while i != -1:
    print('--- occurrence at', i)
    print(src[max(0,i-1200):i+800])
    i = src.find("'hazen'", i+1)
    if i > 60000: break
