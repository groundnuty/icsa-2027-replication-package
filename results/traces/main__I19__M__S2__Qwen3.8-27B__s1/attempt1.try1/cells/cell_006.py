import numpy as np, inspect
import numpy.lib._function_base_impl as F
names = [n for n in dir(F) if 'quant' in n.lower()]
print(names)
for n in names:
    obj = getattr(F, n)
    if callable(obj):
        try:
            src = inspect.getsource(obj)
            if 'hazen' in src:
                print("="*30, n, "="*30)
                print(src[:4000])
        except Exception:
            pass
