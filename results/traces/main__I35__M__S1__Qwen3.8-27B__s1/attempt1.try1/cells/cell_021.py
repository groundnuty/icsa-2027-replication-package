import numpy as np
v = np.array([1., 2., 3., 4.])
for m in ("linear", "hazen", "weibull", "median_unbiased", "normal_unbiased"):
    print(m, np.quantile(v, 0.9, method=m))
v121 = np.arange(1., 122.)
for m in ("linear", "hazen"):
    print("n=121", m, np.quantile(v121, 0.9, method=m))
