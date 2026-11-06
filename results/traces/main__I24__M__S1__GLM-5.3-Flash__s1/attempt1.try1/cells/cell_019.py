import numpy as np, inspect
import numpy.lib._function_base_impl as fb
d = fb._QuantileMethods['hazen']
print(d)
print(type(d['get_virtual_index']))
print(inspect.getsource(d['get_virtual_index']) if hasattr(d['get_virtual_index'],'__code__') else d['get_virtual_index'])
print('fix_gamma:', d['fix_gamma'])
