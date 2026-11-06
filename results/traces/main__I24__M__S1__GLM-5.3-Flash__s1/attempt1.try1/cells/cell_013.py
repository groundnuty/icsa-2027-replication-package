import numpy as np

def hazen_quantile_rows(P, p=0.9):
    """P: (nrow, m) with NaN. Returns per-row p-quantile matching np.quantile(row[finite],p,method='hazen') bitwise."""
    fin = np.isfinite(P)
    nv = fin.sum(axis=1)
    S = np.sort(np.where(fin, P, np.inf), axis=1)
    h = nv*p - 0.5
    np.clip(h, 0, (nv-1).astype(np.float64), out=h)
    k = np.floor(h)
    g = h - k
    ki = k.astype(np.int64)
    rows = np.arange(P.shape[0])
    a = S[rows, ki]
    b = S[rows, ki+1]
    # replicate numpy _lerp
    diff_b_a = b - a
    q = a + diff_b_a * g
    q = np.where(g >= 0.5, b - diff_b_a*(1-g), q)
    q[nv == 0] = np.nan
    return q

# validation vs np
rng = np.random.default_rng(42)
ok = True
for trial in range(300):
    nrow = 5
    sizes = rng.integers(1, 200, size=nrow)
    P = np.full((nrow, sizes.max()), np.nan)
    for r, n in enumerate(sizes):
        vals = rng.normal(280, 5, size=n)
        # sprinkle float32-like values
        if rng.random() < 0.5: vals = vals.astype(np.float32).astype(np.float64)
        nn = rng.integers(0, n+1)
        idx = rng.choice(n, size=n-nn, replace=False)
        P[r, idx] = np.nan
        P[r, idx.size:] = np.nan
        P[r, :nn] = vals[:nn]  # only first nn slots finite
    mine = hazen_quantile_rows(P)
    for r, n in enumerate(sizes):
        ref = np.quantile(P[r][np.isfinite(P[r])], 0.9, method='hazen') if np.isfinite(P[r]).any() else np.nan
        if np.isnan(ref):
            eq = np.isnan(mine[r])
        else:
            eq = (mine[r] == ref) or np.isnan(mine[r])==np.isnan(ref) and mine[r]==ref
        if not eq:
            ok = False
            print('MISMATCH trial',trial,'row',r,'n',n, repr(mine[r]), repr(ref))
print('random validation exact-match:', ok)

# also n=121 and n=33 exactly, with float32-derived values
for n in [121, 33]:
    P = np.full((200, n), np.nan)
    vals = (rng.normal(285, 2, size=(200, n))).astype(np.float32).astype(np.float64)
    nfin = np.full(200, n); nfin[::7] = n-10; nfin[::13] = 1; nfin[::29] = n//2
    for r in range(200):
        idx = rng.choice(n, size=int(nfin[r]), replace=False)
        P[r, idx] = vals[r, idx]
    mine = hazen_quantile_rows(P)
    ref = np.array([np.quantile(P[r][np.isfinite(P[r])],0.9,method='hazen') for r in range(200)])
    print(n, 'exact:', np.array_equal(mine, ref, equal_nan=True))
