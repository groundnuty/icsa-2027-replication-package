import numpy as np, inspect
mod = inspect.getmodule(np.quantile)
print(mod.__name__, mod.__file__)
src = inspect.getsource(mod)
i = src.find("hazen")
while i != -1:
    print("---- at", i)
    print(src[max(0,i-600):i+300])
    i = src.find("hazen", i+1)
    if i > 20000: break
