import numpy, inspect, glob, re
import numpy.lib._nanfunctions_impl as nf
src = inspect.getsource(nf)
for m in re.finditer(r'.*hazen.*', src):
    print(m.group(0))
print('---')
# find virtual index computation
i = src.find('virtual_index')
print(src[max(0,i-3000):i+1500] if i>0 else "not found")
