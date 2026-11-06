import numpy, inspect, re
from numpy.lib import function_base as fb
import numpy.lib._npyio_impl  # noqa
# find the quantile implementation source
import numpy._core.functions as fns  # may not exist; fallback below
try:
    import numpy.lib.function_base as fb2
    src = inspect.getsource(fb2._quantile_implementation)
except Exception as e:
    print("try1 failed", e)
    import numpy
    mod = numpy.__import__("numpy._core.functions", fromlist=["x"]) if hasattr(numpy,'_core') else None
    src = None
if src is None:
    import importlib
    m = importlib.import_module("numpy._core.functions")
    src = inspect.getsource(m._quantile_implementation)
i = src.find("hazen")
print(src[max(0,i-3000):i+2000])
