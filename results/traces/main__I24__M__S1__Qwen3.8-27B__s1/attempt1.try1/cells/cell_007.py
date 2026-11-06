import numpy as np
q = 0.9
for n in [1,2,3,4,5,6,10,11,21,31,51,100,121]:
    v = np.arange(n, dtype=float)
    r = np.quantile(v, q, method='hazen')
    print(n, r)
