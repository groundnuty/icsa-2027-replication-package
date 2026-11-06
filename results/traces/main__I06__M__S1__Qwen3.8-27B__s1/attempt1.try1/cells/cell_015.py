import numpy as np, os
base = os.path.dirname(np.__file__)
for root, dirs, files in os.walk(base):
    for f in files:
        if f.endswith(".py"):
            p = os.path.join(root, f)
            try: t = open(p, encoding="utf-8").read()
            except: continue
            if "hazen" in t:
                print("FILE:", p)
                i = t.find("hazen")
                print(t[max(0,i-1500):i+500])
