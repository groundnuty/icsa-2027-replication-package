
import numpy, inspect
import numpy.lib._nanfunctions_impl as nf
src = inspect.getsource(nf)
i = src.find('hazen')
while i != -1:
    print(repr(src[i-400:i+400]))
    print('='*80)
    i = src.find('hazen', i+1)
    if i > 20000: break
