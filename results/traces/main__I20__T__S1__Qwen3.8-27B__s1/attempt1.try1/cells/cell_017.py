import numpy, inspect, re
from numpy.lib._function_base_impl import _quantile_uses, _quantile
src = inspect.getsource(_quantile)
# find the section handling method formulas
m = re.search(r"method in \{.*?\}.*?\nh = .{0,80}", src, re.S)
idx = src.find("h = (n")
print(src[idx-2000:idx+1500] if idx>0 else "pattern not found")