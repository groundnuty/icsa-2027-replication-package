import numpy as np
rng = np.random.default_rng(1)

def interp_pos(x, r):
    # find i (0-based lower) and frac such that r = x[i] + frac*(x[i+1]-x[i])
    n = len(x)
    for i in range(n-1):
        if x[i] <= r <= x[i+1] and x[i+1] > x[i]:
            return i, (r - x[i])/(x[i+1]-x[i])
    if r == x[0]: return 0, 0.0
    if r == x[-1]: return n-1, 1.0
    return None, None

for q in [0.25, 0.5, 0.75, 0.9]:
    print("q =", q)
    for n in [1,2,5,9,10,11,15,20,50]:
        x = np.sort(rng.normal(288, 2, n))
        r = np.quantile(x, q, method='hazen')
        i, frac = interp_pos(x, r)
        pos = i + frac  # 0-based continuous position
        h = pos + 1     # 1-based
        # candidate formulas for h
        f1 = (n+1)*q
        f2 = (n-1)*q
        print(f"  n={n:3d} pos0={pos:8.4f} h={h:9.4f}  (n+1)q={f1:9.4f}  (n-1)q={f2:9.4f}")
