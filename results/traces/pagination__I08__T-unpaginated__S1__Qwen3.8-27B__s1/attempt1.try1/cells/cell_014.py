
import numpy, inspect, re
import numpy.lib._nanfunctions_impl as nf
src = inspect.getsource(nf)
# find the methods table
m = re.search(r"def _get_methods.*?(?=\ndef |\nclass )", src, re.S)
print(m.group(0)[:3000] if m else "pattern not found")
