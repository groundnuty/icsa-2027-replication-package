import numpy as np
# Reverse engineer numpy 'hazen': use a=1..n so quantile == h (the interpolation position, 1-based)
for n in [2,3,5,10,20,50,121]:
    a = np.arange(1, n+1, dtype=float)
    v = np.quantile(a, 0.9, method="hazen")
    print(n, v)
