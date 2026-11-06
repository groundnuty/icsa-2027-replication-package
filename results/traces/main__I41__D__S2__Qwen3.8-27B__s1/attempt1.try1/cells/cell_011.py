import numpy as np, inspect
import numpy.lib._function_base_impl as fb
src = inspect.getsource(fb)
import re
for m in re.finditer(r'def [a-zA-Z_]*quantile[a-zA-Z_]*', src):
    print(m.group())
print("---- hazen mentions ----")
for m in re.finditer(r'hazen', src):
    s = max(0, m.start()-400)
    print(src[s:m.end()+400])
    print('======')
