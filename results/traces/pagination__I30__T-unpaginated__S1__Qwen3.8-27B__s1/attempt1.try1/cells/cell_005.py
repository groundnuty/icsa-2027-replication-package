
import numpy as np
# verify hazen quantile definition
x = np.arange(1, 122, dtype=float)  # 1..121
q_hazen = np.nanquantile(x, 0.9, method='hazen')
n = 121
# HF type 8: h = (n+0.5)*p + 0.5 (1-indexed); type 5: h = (n+1)*p; type 7: h = 1+(n-1)*p
for name, h in [('type5',(n+1)*0.9), ('type7',1+(n-1)*0.9), ('type8',(n+0.5)*0.9+0.5)]:
    lo = int(np.floor(h)); frac = h - lo
    val = x[lo-1] + frac*(x[lo]-x[lo-1]) if lo < n else x[n-1]
    print(name, h, val)
print('numpy hazen:', q_hazen)
