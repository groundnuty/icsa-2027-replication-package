import numpy as np
a = np.array([np.nan, 1.0, 2.0, 3.0, 4.0, 5.0])
print("hazen nan:", np.nanquantile(a, 0.9, method="hazen"))
print("linear nan:", np.nanquantile(a, 0.9, method="linear"))
b = np.array([1.,2,3,4,5])
print("hazen:", np.quantile(b, 0.9, method='hazen'))   # h=(5+1)*.9=5.4 -> clamp to 5? expect 5.0
print("linear:", np.quantile(b, 0.9, method='linear')) # (n-1)*.9=3.6 -> 4.6
