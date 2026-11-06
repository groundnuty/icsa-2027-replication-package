import importlib, sys
print(sys.version)
import numpy, xarray
print("numpy", numpy.__version__)
print("xarray", xarray.__version__)
try:
    import h5py; print("h5py", h5py.__version__)
except Exception as e:
    print("h5py missing", e)
try:
    from scipy import signal; print("scipy ok")
except Exception as e:
    print("scipy missing", e)
import numpy as np
a = np.array([1.,2.,3.,4.])
try:
    print(np.nanquantile(a, 0.9, method="hazen"))
except Exception as e:
    print("no method kw:", e)
