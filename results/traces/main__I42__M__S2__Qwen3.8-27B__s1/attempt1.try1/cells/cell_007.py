import numpy as np
print("numpy:", np.__version__)

# Verify hazen (HF type 6: h=(n+1)p 1-based) behavior
x = np.arange(1, 11, dtype=float)
print("n=10 hazen 0.9:", np.quantile(x, 0.9, method='hazen'))   # expect 9.9
xnan = np.concatenate([x, [np.nan]])
print("n=10+NaN hazen 0.9:", np.nanquantile(xnan, 0.9, method='hazen'))  # expect 9.9
x11 = np.arange(1, 12, dtype=float)
print("n=11 hazen 0.9:", np.nanquantile(x11, 0.9, method='hazen')) # expect 10.8
# compare with MATLAB linear (type 7): (n-1)p+1 -> for n=121: 109th 1-based
# check nanquantile with NaN in interior
y = np.array([np.nan, 2.0, 1.0, 4.0, 3.0])
print("sorted-nan hazen 0.9 n=4:", np.nanquantile(y, 0.9, method='hazen'))  # h=5*0.9=4.5 -> 3+0.5*(4-3)=3.5
