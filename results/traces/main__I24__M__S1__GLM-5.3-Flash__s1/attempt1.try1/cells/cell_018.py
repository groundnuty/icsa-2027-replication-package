import numpy as np, inspect, re
src = inspect.getsource(np.lib._function_base_impl._QuantileMethods) if hasattr(np.lib._function_base_impl,'_QuantileMethods') else None
import numpy.lib._function_base_impl as fb
m = re.search(r'_QuantileMethods\s*=\s*\{.*?\n\}', inspect.getsource(fb), re.S)
print(m.group(0)[:2500] if m else 'not found')
