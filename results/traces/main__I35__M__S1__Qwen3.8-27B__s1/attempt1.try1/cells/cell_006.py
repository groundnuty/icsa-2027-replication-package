import numpy as np, sys
print(np.__version__, sys.version)
# test nanquantile method hazen
x = np.array([1.0, 2.0, 3.0, np.nan, 5.0])
print(np.nanquantile(x, 0.9, method="hazen"))
print(np.nanquantile(x, 0.9, method="linear"))
