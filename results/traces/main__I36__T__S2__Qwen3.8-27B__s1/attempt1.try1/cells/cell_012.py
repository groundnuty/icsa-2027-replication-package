import numpy as np, inspect
import numpy.lib._function_base_impl as F
src = inspect.getsource(F)
import re
i = src.find('_hazen')
print(src[i-200:i+300] if i>=0 else 'not found in function_base')
# find the methods dict
j = src.find('default_methods')
print(src[j-50:j+400] if j>=0 else 'no default_methods')
