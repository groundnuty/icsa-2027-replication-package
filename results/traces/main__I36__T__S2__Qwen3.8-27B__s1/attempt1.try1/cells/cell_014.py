import numpy as np
rng = np.random.default_rng(42)
x = rng.random(121)
q_np = float(np.quantile(x, 0.9, method='hazen'))
xs = np.sort(x); n = len(xs)
v = 0.9*n + 0.5 - 1          # numpy hazen virtual index (0-based)
j = int(np.floor(v)); g = v - j
q_manual = xs[j] + g*(xs[j+1]-xs[j])
print('np', q_np, 'manual', q_manual, 'match', np.isclose(q_np, q_manual))

# also check with NaN ignored (sample size shrinks)
xn = x.copy(); xn[0] = np.nan; xn[50] = np.nan
q_np2 = float(np.nanquantile(xn, 0.9, method='hazen'))
xs2 = np.sort(xn[~np.isnan(xn)]); n2 = len(xs2)
v2 = 0.9*n2 + 0.5 - 1
j2 = int(np.floor(v2)); g2 = v2 - j2
q_manual2 = xs2[j2] + g2*(xs2[j2+1]-xs2[j2])
print('np nan', q_np2, 'manual nan', q_manual2, 'match', np.isclose(q_np2, q_manual2))
