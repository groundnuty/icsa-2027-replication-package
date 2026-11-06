import numpy as np, inspect
import numpy.lib._function_base_impl as fb
for fn in ['_get_indexes','_get_gamma','_lerp']:
    print('='*20, fn)
    print(inspect.getsource(getattr(fb, fn)))
# also the hazen virtual index def
import re
m = re.search(r'"hazen".{0,400}', inspect.getsource(fb), re.S)
print(m.group(0) if m else 'not found')
