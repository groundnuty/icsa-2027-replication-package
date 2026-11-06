import numpy as np, xarray as xr, sys
print(sys.version)
print("numpy", np.__version__, "xarray", xr.__version__)

# test nanquantile method support
a = np.array([[1.0, np.nan], [2.0, 3.0], [4.0, 5.0], [6.0, 7.0], [8.0, 9.0]])
try:
    print(np.nanquantile(a, 0.9, method="hazen", axis=0))
except Exception as e:
    print("ERR", e)
# reference hazen for [1..9]: h=(9+1)*0.9=9 -> x[9] (1-based) = 9
print("manual check:", np.quantile(np.arange(1,10), 0.9, method="hazen"))
