import numpy as np, inspect
import numpy.lib as nl
mods = [m for m in nl.__all__ if 'func' in m.lower()]
print(mods)
import numpy.lib.function_base as fb
cands = [n for n in dir(fb) if 'quantile' in n.lower()]
print(cands)
print(inspect.getsource(fb._quantile_hazen))
