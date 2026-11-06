import numpy as np, inspect
import numpy.lib._nanfunctions_impl as nf
print(inspect.getsource(nf._nanquantile_1d))
