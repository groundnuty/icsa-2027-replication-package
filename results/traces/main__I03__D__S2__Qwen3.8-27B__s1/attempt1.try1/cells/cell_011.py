import numpy as np
rng = np.random.default_rng(0)
for n in [1,2,3,5,9,10,11,20]:
    x = np.sort(rng.normal(288, 2, n))
    a = np.quantile(x, 0.9, method='hazen')
    # candidate: HF type5 with clamp: h=(n+1)p; i=floor(h); frac; val = x[i-1] + frac*(x[i]-x[i-1]), clamp indices to [1,n]
    h = (n+1)*0.9
    i = int(np.floor(h)); frac = h - i
    lo = min(max(i,1), n); hi = min(max(i+1,1), n)
    val = x[lo-1] + frac*(x[hi-1]-x[lo-1])
    print(n, "x=", np.round(x,3), "numpy=%.9f" % a, "clamp5=%.9f" % val, np.isclose(a,val))
