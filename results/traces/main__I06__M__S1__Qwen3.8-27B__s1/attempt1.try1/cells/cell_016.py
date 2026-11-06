import numpy as np, os
base = os.path.dirname(np.__file__)
p = os.path.join(base, "lib", "_function_base_impl.py")
t = open(p, encoding="utf-8").read()
i = t.find("def _compute_virtual_index")
print(t[i:i+800])
j = t.find("'linear':")
print(t[j:j+500])
# and the interpolation core
k = t.find("def _quantile")
print(t[k:k+2600])
