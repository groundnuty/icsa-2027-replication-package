import numpy as np
print("numpy", np.__version__)
x = np.array([1.,2.,3.,4.])
for m in ["hazen","linear"]:
    print(m, [np.quantile(x, p, method=m) for p in [0.1,0.5,0.9,0.95]])
# hazen: h = n*p (1-based): p=0.9,n=4 -> h=3.6 -> x[3] + 0.6*(x[4]-x[3]) = 3.6
# hazen n=121 p=0.9 -> h = 108.9
x121 = np.arange(1,122,dtype=float)
print("hazen n=121 p=0.9:", np.quantile(x121, 0.9, method="hazen"), "expected", 108 + 0.9)
# with NaN
xnan = x121.copy(); xnan[0]=np.nan
print("nanquantile hazen:", np.nanquantile(xnan, 0.9, method="hazen"), "expected", np.quantile(xnan[1:],0.9,method="hazen"))
import netCDF4
print("netCDF4", netCDF4.__version__)
