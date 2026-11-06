import numpy, inspect, re
src = inspect.getsource(numpy._core._methods._quantile)
print(src[:6000])
