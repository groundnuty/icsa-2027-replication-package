import numpy as np
print("numpy", np.__version__)
# reverse-engineer numpy hazen position for various n
for n in [2, 3, 5, 10, 121]:
    x = np.arange(1, n + 1, dtype=float)
    v = np.quantile(x, 0.9, method='hazen')
    # candidate formulas (0-based h)
    cands = {
        'nq-0.5': n*0.9 - 0.5,
        '(n-1)q+0.5': (n-1)*0.9 + 0.5,
        '(n+1)q-1': (n+1)*0.9 - 1,
        '(n-1)q': (n-1)*0.9,
        '(n+1/3)q-1/3': (n+1/3)*0.9 - 1/3,
        '(n+1)q-0.375': (n+1)*0.9 - 0.375,
    }
    def val(h):
        h = min(max(h, 0.0), n-1.0000001)
        j = int(h); g = h - j
        if g < 1e-15 or j >= n-1:
            return x[j]
        return x[j] + g*(x[j+1]-x[j])
    got = {k: val(v) for k, v in cands.items()}
    best = [k for k in got if abs(got[k] - v) < 1e-12]
    print(f"n={n}: quantile={v}  matches={best}")

# nanquantile with method support
X = np.array([[1.,2,3,4,5],[np.nan,2,3,4,5],[np.nan,np.nan,3,4,5],[1.,2,3,4,5]])
try:
    print(np.nanquantile(X, 0.9, axis=1, method='hazen'))
    print("refs:", [np.quantile(r[~np.isnan(r)], 0.9, method='hazen') if np.isfinite(r).any() else np.nan for r in X])
except TypeError as e:
    print("nanquantile method not supported:", e)
