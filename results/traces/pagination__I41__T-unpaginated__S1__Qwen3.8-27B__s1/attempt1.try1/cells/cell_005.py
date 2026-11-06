
import numpy as np
print("numpy:", np.__version__)
x = np.array([1.,2.,3.,4.,5.])
print("hazen 0.9:", np.quantile(x, 0.9, method="hazen"))
print("linear 0.9:", np.quantile(x, 0.9, method="linear"))
# MATLAB quantile([1 2 3 4 5],0.9) = 4.6
y = np.array([1.,np.nan,3.,4.,5.])
print("nanquantile hazen 0.9:", np.nanquantile(y, 0.9, method="hazen"))
# small check n=3 values [10,20,30], p=0.9: type5/linear: 1+(3-1)*.9=2.8 -> 20+.8*10=28
print("n=3:", np.quantile(np.array([10.,20.,30.]),0.9,method="hazen"))
