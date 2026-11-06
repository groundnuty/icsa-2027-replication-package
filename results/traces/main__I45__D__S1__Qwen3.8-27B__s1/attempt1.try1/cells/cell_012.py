import numpy as np, inspect
import numpy.lib._function_base as fb
src = inspect.getsource(fb._quantile_hazen) if hasattr(fb, '_quantile_hazen') else None
print(src)
# find the method name
print([n for n in dir(fb) if 'quant' in n.lower()][:40])
x = np.array([1.,2,3,4,5])
for p in [0.1,0.2,0.3,0.5,0.7,0.9]:
    print(p, np.quantile(x, p, method='hazen'))
v = np.random.default_rng(42).normal(280,5,121); vs = np.sort(v)
print("numpy hazen 0.9 n=121:", np.quantile(v,0.9,method='hazen'))
print("vs[108:111]:", vs[108:111])
# solve position
target = np.quantile(v,0.9,method='hazen')
import math
for i in range(106,112):
    if vs[i] <= target <= vs[i+1]:
        g = (target-vs[i])/(vs[i+1]-vs[i])
        print("interp between idx", i, "and", i+1, "g=", g, "=> 1-based pos", i+1+g)
