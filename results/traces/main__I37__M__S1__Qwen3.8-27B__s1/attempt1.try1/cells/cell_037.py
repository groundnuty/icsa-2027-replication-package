import numpy, os, re
root = os.path.dirname(numpy.__file__)
hits = []
for dp, _, fns in os.walk(root):
    for fn in fns:
        if fn.endswith(('.py',)):
            p = os.path.join(dp, fn)
            try:
                s = open(p, encoding='utf8', errors='ignore').read()
            except Exception:
                continue
            for m in re.finditer(r'.*hazen.*', s):
                hits.append((p, m.group(0).strip()))
for p, l in hits[:40]:
    print(p.replace(root, ''))
    print("   ", l[:160])
