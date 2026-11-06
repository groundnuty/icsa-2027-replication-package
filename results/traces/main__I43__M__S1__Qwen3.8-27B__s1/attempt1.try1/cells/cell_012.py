import numpy, os, re
root = os.path.dirname(numpy.__file__)
hits = []
for dirpath, dirs, files in os.walk(root):
    for f in files:
        if f.endswith(".py"):
            p = os.path.join(dirpath, f)
            try:
                s = open(p, encoding="utf-8").read()
            except Exception:
                continue
            if "hazen" in s:
                hits.append((p, s.count("hazen")))
print(hits[:20])
