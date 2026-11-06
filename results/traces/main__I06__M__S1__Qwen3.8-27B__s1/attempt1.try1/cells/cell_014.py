import numpy as np, numpy.core._methods  # noqa
import numpy.lib
import pkgutil, os
base = os.path.dirname(np.__file__)
hits = []
for root, dirs, files in os.walk(base):
    for f in files:
        if f.endswith(".py"):
            p = os.path.join(root, f)
            try:
                t = open(p, encoding="utf-8").read()
            except Exception:
                continue
            if "hazen" in t:
                hits.append(p)
print(hits)
