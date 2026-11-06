import numpy as np, inspect
import numpy._core._methods as M
src = inspect.getsource(M)
idxs = [m.start() for m in __import__('re').finditer('hazen', src)]
print(len(idxs))
if idxs:
    print(src[idxs[0]-3000:idxs[0]+2000])
