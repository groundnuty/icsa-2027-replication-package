
import numpy as np
# verify numpy 'hazen' matches Hyndman-Fan type 5: h = (n+1/3)*p (1-based)
rng = np.random.default_rng(0)
x = rng.random(1000)
for p in [0.9]:
    v_hazen = np.quantile(x, p, method='hazen')
    # type 5: h = (n + 1/3) p
    n = len(x)
    xs = np.sort(x)
    h = (n + 1/3) * p
    k = np.floor(h) - 1  # 0-based lower index
    g = h - (k+1)
    v_t5 = xs[int(k)] + g * (xs[min(int(k)+1, n-1)] - xs[int(k)])
    print("hazen:", v_hazen, "type5:", v_t5)
# also check 'linear' for reference (type 7: h=(n-1)p+1)
v_lin = np.quantile(x, 0.9, method='linear')
h7 = (n-1)*0.9 + 1
k7 = np.floor(h7) - 1
g7 = h7 - (k7+1)
v_t7 = xs[int(k7)] + g7*(xs[int(k7)+1]-xs[int(k7)])
print("linear:", v_lin, "type7:", v_t7)
print("quantile signature ok:", np.nanquantile(np.array([[1.0,np.nan],[2.0,3.0]]), 90, axis=0, method='hazen'))
