
import numpy as np
x = np.arange(1, 122, dtype=float)
print("numpy hazen p=0.9, n=121:", np.quantile(x, 0.9, method="hazen"))
print("numpy weibull p=0.9:", np.quantile(x, 0.9, method="weibull"))
print("numpy linear p=0.9:", np.quantile(x, 0.9, method="linear"))
x2 = np.arange(1, 6, dtype=float)
for m in ["hazen","weibull","linear"]:
    print(m, "n=5:", np.quantile(x2, 0.9, method=m), np.quantile(x2, 0.5, method=m))
# inspect numpy source formula
import inspect, numpy._core._methods as M
src = inspect.getsource(M._quantile_1d)
import re
for line in src.splitlines():
    if "hazen" in line or ("h =" in line) or "elif method" in line:
        print(line)
