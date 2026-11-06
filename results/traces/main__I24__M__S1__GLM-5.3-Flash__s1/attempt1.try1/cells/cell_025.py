import numpy as np, inspect, re
import numpy.lib._function_base_impl as fb
# find nan handling path in np.quantile / np.nanquantile
src = inspect.getsource(fb.np.quantile) if False else None
# locate _nanquantile in numpy lib
import numpy.lib as nfl
print([n for n in dir(fb) if 'nan' in n.lower()])
import numpy.lib._nanfunctions_impl as nf
print([n for n in dir(nf) if 'quant' in n.lower() or 'percent' in n.lower()])
src = inspect.getsource(nf._nanquantile)
print(src[:3000])
