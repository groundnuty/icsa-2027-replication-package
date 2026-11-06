
import numpy as np
import inspect

# Get the source of the percentile function
from numpy.lib._function_base_impl import percentile
print(inspect.getsource(percentile))
