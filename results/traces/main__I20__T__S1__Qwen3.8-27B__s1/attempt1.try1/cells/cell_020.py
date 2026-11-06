import inspect
from numpy.lib import _function_base_impl as F
src = inspect.getsource(F)
i = src.find("'hazen'")
print(src[i:i+400])
print("---- weibull")
j = src.find("'weibull'")
print(src[j:j+400])