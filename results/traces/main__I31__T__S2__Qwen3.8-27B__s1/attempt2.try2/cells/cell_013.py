import numpy as np

def nanquantile_hazen_rows(X):
    X = np.ascontiguousarray(X, dtype=np.float64)
    C, M = X.shape
    nan = np.isnan(X)
    n = M - nan.sum(axis=1)
    Xs = np.sort(np.where(nan, np.inf, X), axis=1)
    h = (n + 1) * 0.9 - 1.0
    j = np.floor(h).astype(np.int64)
    j = np.clip(j, 0, np.maximum(n - 1, 0))
    g = h - j
    rows = np.arange(C)
    v1 = Xs[rows, j]
    jj2 = np.minimum(j + 1, np.maximum(n - 1, 0))
    v2 = Xs[rows, jj2]
    use = (g > 0) & (j + 1 < n)
    res = np.where(use, v1 + g * (v2 - v1), v1)
    res = np.where(n > 0, res, np.nan)
    return res

# minimal checks
X = np.array([[1.,2,3,4,5,6,7,8,9,10]])
print("clean:", nanquantile_hazen_rows(X), np.quantile(np.arange(1,11.0), 0.9, method='hazen'))

rng = np.random.default_rng(0)
Xt = rng.normal(300, 5, (200, 121))
Xt[rng.random(Xt.shape) < 0.08] = np.nan
got = nanquantile_hazen_rows(Xt)
ref = np.array([np.quantile(Xt[r][~np.isnan(Xt[r])], 0.9, method='hazen') for r in range(200)])
diff = np.abs(got - ref)
i = np.argmax(diff)
print("max diff:", diff.max(), "at row", i, "n_valid:", np.isfinite(Xt[i]).sum())
print("got", got[i], "ref", ref[i])
Xrow = Xt[i][~np.isnan(Xt[i])]
h = (len(Xrow)+1)*0.9 - 1
print("h", h, "j", int(h), "g", h-int(h))
print("x[j], x[j+1]:", Xrow[int(h)], Xrow[int(h)+1] if int(h)+1 < len(Xrow) else None)
# scan all rows for mismatches > 1e-9
bad = np.where(diff > 1e-9)[0]
print("num bad rows:", len(bad), bad[:10])
if len(bad):
    r = bad[0]
    Xrow = Xt[r][~np.isnan(Xt[r])]
    n = len(Xrow); h = (n+1)*0.9-1; j = int(h)
    print("row", r, "n", n, "h", h, "j", j, "got", got[r], "ref", ref[r])
    print("sorted tail:", Xrow[j-2:j+3])
