import numpy, inspect, importlib, os
cands = []
root = os.path.dirname(numpy.__file__)
for dp, dn, fn in os.walk(os.path.join(root, "_core")):
    for f in fn:
        if "function" in f or "quantile" in f:
            cands.append(os.path.join(dp, f))
print(cands)
for c in cands:
    try:
        m = importlib.import_module("numpy._core." + os.path.relpath(c, root).replace(os.sep,'.')[:-3].split('.')[-1])
        if hasattr(m, '_quantile_implementation'):
            print("FOUND in", m.__name__)
            src = inspect.getsource(m._quantile_implementation)
            i = src.find("hazen")
            print(src[max(0,i-2500):i+1500])
            break
    except Exception as e:
        print("fail", c, e)
