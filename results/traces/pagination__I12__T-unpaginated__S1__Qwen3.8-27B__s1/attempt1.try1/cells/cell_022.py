import numpy as np, inspect, re
# find the quantile implementation
from numpy._core import _methods  # may not exist
import numpy
src = inspect.getsource(numpy.quantile)
print(src[:2000])