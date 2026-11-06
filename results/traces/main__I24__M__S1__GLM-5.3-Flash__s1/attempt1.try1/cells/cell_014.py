import numpy as np

def hazen_quantile_rows(P, p=0.9):
    """Per-row hazen quantile of finite values, replicating np.quantile(method='hazen') arithmetic exactly."""
    fin = np.isfinite(P)
    nv = fin.sum(axis=1)
    S = np.sort(np.where(fin, P, np.inf), axis=1)
    h = nv.astype(np.float64)*p - 0.5          # virtual index (numpy: n*p + alpha/(alpha+beta) - 0.5... empirically n*p-0.5)
    # clip virtual index like numpy does for indexes (it clips the resulting int indexes)
    k = np.floor(h)
    ki = np.clip(k.astype(np.int64), 0, nv-1)          # previous, clipped
    ki1 = np.clip(ki+1, 0, nv-1)                        # next, clipped
    g = h - ki.astype(np.float64)
    rows = np.arange(P.shape[0])
    a = S[rows, ki]
    b = S[rows, ki1]
    diff = b - a
    l = a + diff * g
    sub = diff * g * (1 - g)
    l = np.where(g >= 0.5, l - sub, l)
    l[nv == 0] = np.nan
    return l

# validation, proper harness
rng = np.random.default_rng(42)
ok = True; nchecked=0
for trial in range(400):
    nrow = 6
    P = rng.normal(280, 5, size=(nrow, 200))
    if rng.random()<0.5: P = P.astype(np.float32).astype(np.float64)
    for r in range(nrow):
        nn = int(rng.integers(0, 201))
        idx = rng.permutation(200)[:nn]
        row = np.full(200, np.nan)
        row[idx] = P[r, idx]
        P[r] = row
    mine = hazen_quantile_rows(P)
    for r in range(nrow):
        nchecked+=1
        fin = np.isfinite(P[r])
        ref = np.quantile(P[r][fin], 0.9, method='hazen') if fin.any() else np.nan
        eq = (mine[r] == ref) if not np.isnan(ref) else np.isnan(mine[r])
        if not eq:
            ok = False
            print('MISMATCH t',trial,'r',r,'nv',fin.sum(), repr(mine[r]), repr(ref))
print('random validation rows:',nchecked,'exact match:', ok)

# fixed-size tests incl nv=121, 33, 5, 11 with float32 values
for n in [121, 33, 11, 5, 2, 1]:
    bad=0
    for rep in range(50):
        P = (rng.normal(285, 2, size=(50, n))).astype(np.float32).astype(np.float64)
        fin = rng.random(size=(50,n)) < 0.9
        P[~fin] = np.nan
        mine = hazen_quantile_rows(P)
        ref = np.array([np.quantile(P[r][np.isfinite(P[r])],0.9,method='hazen') if np.isfinite(P[r]).any() else np.nan for r in range(50)])
        good = np.array_equal(mine, ref, equal_nan=True)
        bad += 0 if good else 1
    print('n=%d bad reps: %d/50'%(n,bad))
