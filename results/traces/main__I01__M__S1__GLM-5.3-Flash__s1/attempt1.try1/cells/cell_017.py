import numpy as np
rng = np.random.default_rng(42)
# candidate: hazen 1-based position = p*n + 0.5  (numpy: virtual_index = q*n - 0.5, 0-based)
for n in [1,2,3,4,5,7,10,50,101,337]:
    vals = rng.normal(size=n)
    ref = np.quantile(vals, 0.9, method='hazen')
    s = np.sort(vals)
    g0 = 0.9*n + 0.5
    lo, hi = int(np.floor(g0)), int(np.ceil(g0))
    lo_c, hi_c = max(1,lo), min(n,max(1,hi))
    v = s[lo_c-1] + (g0-lo_c)*(s[hi_c-1]-s[lo_c-1]) if hi_c>lo_c else s[lo_c-1]
    # careful when g0>n
    ok = abs(v-ref) < 1e-12
    print(n, f'{ref:.10f}', f'{v:.10f}', ok)
