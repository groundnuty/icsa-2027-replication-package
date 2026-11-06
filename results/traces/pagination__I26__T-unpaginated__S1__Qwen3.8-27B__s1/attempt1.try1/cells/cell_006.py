import numpy, sys, os
print("numpy:", numpy.__version__)
print("cwd:", os.getcwd())
import shutil
print(shutil.disk_usage(os.getcwd()))
# verify nanquantile supports method
a = np.array([np.nan, 1.0, 2.0, 3.0, 4.0, 5.0])
print(np.nanquantile(a, 0.9, method="hazen"))
print(np.nanquantile(a, 0.9, method="linear"))
# manual hazen check: finite = 1..5, n=5, h=(n+1)*0.9=5.4 -> 5th order stat + 0.4*(...)? h=5.4: floor 5, frac .4 -> x[4]*(1-.4) + x[5]? out of range!
# Hazen: h = (n+1)p = 5.4; but h must be <= n? Standard definition: h in (0, n+1]; if h > n then h = n.
# Let's check numpy behavior: np.quantile([1..5], 0.9, method='hazen')
print(np.quantile(np.array([1.,2,3,4,5]), 0.9, method='hazen'))
