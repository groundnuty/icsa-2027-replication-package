import numpy as np, numpy, os, re
root = os.path.dirname(numpy.__file__)
hits = []
for dp, _, fns in os.walk(root):
    for fn in fns:
        if fn.endswith('.py'):
            p = os.path.join(dp, fn)
            try:
                s = open(p, encoding='utf-8', errors='ignore').read()
            except Exception:
                continue
            if "'hazen'" in s or '"hazen"' in s:
                hits.append(p)
print(hits)
p = hits[0]
s = open(p, encoding='utf-8').read()
i = s.find('hazen')
while i != -1:
    print('---', p, i)
    print(s[max(0,i-1500):i+500])
    i = s.find('hazen', i+1)
    if i > 20000:
        break