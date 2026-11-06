
import numpy, inspect
import numpy.lib._nanfunctions_impl as nf
src = inspect.getsource(nf)
import re
for pat in ['c1', 'method', 'hazen']:
    idxs = [m.start() for m in re.finditer(pat, src)]
    print(pat, len(idxs))
# print around occurrences of 'c1'
for m in list(re.finditer(r'\bc1\b', src))[:10]:
    i = m.start()
    print(repr(src[i-200:i+300]))
    print('-'*60)
