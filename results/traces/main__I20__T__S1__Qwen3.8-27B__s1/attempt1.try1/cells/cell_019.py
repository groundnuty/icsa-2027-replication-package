import inspect
from numpy.lib import _function_base_impl as F
qm = F._QuantileMethods
for name, props in qm.items():
    try:
        g = props["get_virtual_index"]
        src = inspect.getsource(g)
        print("====", name)
        print(src)
    except Exception as e:
        print(name, "no get_virtual_index", e)