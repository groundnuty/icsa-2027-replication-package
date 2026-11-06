import numpy as np
rng = np.random.default_rng(42)
x = rng.random(121)
q_np = float(np.quantile(x, 0.9, method='hazen'))
xs = np.sort(x)
n = len(xs)
j = 0.9*(n + 1/3) + 0.5   # HF type 5 1-based position
k = int(np.floor(j)); frac = j - k
q_manual = (xs[k-1] if k-1>=0 else np.nan)
if k < n and frac > 0:
    q_manual = xs[k-1] + frac*(xs[k]-xs[k-1])
elif frac == 0:
    q_manual = xs[k-1]
print('np', q_np, 'manual', q_manual, 'match', np.isclose(q_np, q_manual))
