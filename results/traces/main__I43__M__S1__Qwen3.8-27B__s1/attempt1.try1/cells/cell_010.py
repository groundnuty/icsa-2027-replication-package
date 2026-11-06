import numpy as np, inspect, numpy._core._methods as M
src = inspect.getsource(M)
# find the quantile h calculation
import re
i = src.find("def _quantile_unkind")
print(src[i:i+4000])
