import numpy
import inspect, ast, textwrap
mod = inspect.getmodule(numpy.quantile)
src = inspect.getsource(mod)
# find the function and print via linecache approach: get object then disassemble logic
f = mod._compute_virtual_index
s = inspect.getsource(f)
print(repr(s))
