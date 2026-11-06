import numpy, inspect
import numpy._core._methods as M
cands = [n for n in dir(M) if 'quant' in n.lower() or 'percent' in n.lower()]
print(cands)
src = inspect.getsource(M)
# find hazen mention
idx = src.find('hazen')
print(src[idx-3000:idx+1500])
