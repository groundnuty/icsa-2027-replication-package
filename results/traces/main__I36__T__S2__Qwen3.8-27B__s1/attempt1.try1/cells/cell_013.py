import numpy as np, os, re
root = os.path.dirname(np.__file__)
hits = []
for dirpath, _, files in os.walk(root):
    for fn in files:
        if fn.endswith('.py'):
            p = os.path.join(dirpath, fn)
            try:
                s = open(p, encoding='utf-8').read()
            except Exception:
                continue
            if 'hazen' in s:
                hits.append(p)
print(hits)
p = hits[0]
s = open(p, encoding='utf-8').read()
i = s.find('hazen')
while i != -1:
    print('----', p, i)
    print(s[max(0,i-600):i+200])
    i = s.find('hazen', i+1)
    if i > 200000: break
