import numpy as np, inspect, dis
import numpy.lib._function_base_impl as fb
print(inspect.getsource(fb._compute_virtual_index))
