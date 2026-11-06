import numpy as np

def hazen_rows(P):
    """Exact vectorized replication of np.quantile(row, 0.9, method='hazen') over finite values.
    Follows numpy 2.5.4 _quantile/_get_indexes/_get_gamma/_lerp source exactly."""
    fin = np.isfinite(P)
    nv = fin.sum(axis=1)
    S = np.sort(np.where(fin, P, np.inf), axis=1)   # NaNs -> +inf pad at end (like NaN sorting last)
    n = nv.astype(np.float64)
    # _compute_virtual_index(n, q, alpha=0.5, beta=0.5): n*q + (alpha + q*(1-alpha-beta)) - 1
    virtual = n*0.9 + (0.5 + 0.9*(1 - 0.5 - 0.5)) - 1.0
    # _get_indexes
    previous = np.floor(virtual).astype(np.int64)
    nxt = previous + 1
    above = virtual >= (nv - 1)
    previous = np.where(above, -1, previous)
    nxt = np.where(above, -1, nxt)
    below = virtual < 0
    previous = np.where(below, 0, previous)
    nxt = np.where(below, 0, nxt)
    vnan = np.isnan(virtual)
    previous = np.where(vnan, -1, previous)
    nxt = np.where(vnan, -1, nxt)
    # _get_gamma: gamma = virtual - previous
    gamma = virtual - previous.astype(np.float64)
    rows = np.arange(P.shape[0])
    a = S[rows, previous]
    b = S[rows, nxt]
    # _lerp exact
    diff_b_a = b - a
    l = a + diff_b_a * gamma
    l = np.where(gamma >= 0.5, b - diff_b_a*(1 - gamma), l)
    l[nv == 0] = np.nan
    return l

# debug the previous failing scenario deterministically
rng = np.random.default_rng(7)
for trial in range(3):
    nrow = 40
    m = int(rng.integers(1, 130))
    P = rng.normal(280, 4, size=(nrow, m))
    if rng.random() < 0.5:
        P = P.astype(np.float32).astype(np.float64)
    P = np.ascontiguousarray(P)
    keep = rng.random(size=(nrow, m)) < rng.uniform(0.5, 1.0)
    P[~keep] = np.nan
    if trial % 10 == 0: P[0] = np.nan
    if trial == 0:
        mine = hazen_rows(P)
        r = 3
        fin = np.isfinite(P[r])
        vals = P[r][fin]
        ref = np.quantile(vals, 0.9, method='hazen')
        print('trial0 r3 nv', fin.sum(), 'm', m)
        print('mine', repr(mine[r]), 'ref', repr(ref))
        srt = np.sort(vals)
        nvv = len(vals)
        virtual = nvv*0.9 - 0.5
        import math
        prev = math.floor(virtual)
        print('virtual', virtual, 'prev', prev, 'gamma', virtual-prev)
        print('S[prev],S[prev+1]', repr(srt[prev]), repr(srt[prev+1]))
        manual = srt[prev+1] - (srt[prev+1]-srt[prev])*0.5
        print('manual lerp', repr(manual))
