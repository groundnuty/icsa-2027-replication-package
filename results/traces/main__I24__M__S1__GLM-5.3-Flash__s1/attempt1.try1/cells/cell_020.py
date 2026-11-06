import numpy as np
import numpy.lib._function_base_impl as fb
d = fb._QuantileMethods['hazen']
import dis
print('--- get_virtual_index bytecode ---')
dis.dis(d['get_virtual_index'])
print('--- fix_gamma bytecode ---')
dis.dis(d['fix_gamma'])
