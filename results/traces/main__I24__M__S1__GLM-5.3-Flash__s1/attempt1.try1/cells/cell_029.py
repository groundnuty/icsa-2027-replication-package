import numpy as np

def hazen_rows(P):
    """Exact vectorized replication of np.nanquantile(row, 0.9, method='hazen') per row of P (NaN ignored).
    Replicates numpy 2.5.4 _remove_nan_1d + _quantile + _get_indexes + _get_gamma + _lerp arithmetic."""
    fin = np.isfinite(P)
    nv = fin.sum(axis=1)
    S = np.sort(np.where(fin, P, np.inf), axis=1)   # finite sorted, then +inf pad (NaN sorts last)
    n = nv.astype(np.float64)
    # _compute_virtual_index(n, 0.9, alpha=0.5, beta=0.5): n*0.9 + (0.5 + 0.9*(1-0.5-0.5)) - 1
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
    # -1 in the compacted array = last (max) finite element; map into padded coords
    last = np.maximum(nv - 1, 0).astype(np.int64)
    previous_m = np.where(previous == -1, last, previous)
    nxt_m = np.where(nxt == -1, last, nxt)
    # _get_gamma: virtual - previous (with previous possibly -1)
    gamma = virtual - previous.astype(np.float64)
    rows = np.arange(P.shape[0])
    a = S[rows, previous_m]
    b = S[rows, nxt_m]
    # _lerp, exact op order
    diff_b_a = b - a
    l = a + diff_b_a * gamma
    l = np.where(gamma >= 0.5, b - diff_b_a * (1 - gamma), l)
    l[nv == 0] = np.nan
    return l

def nanmean_rows(P):
    fin = np.isfinite(P)
    P0 = np.where(fin, P, 0.0)
    tot = P0.sum(axis=1)
    cnt = fin.sum(axis=1)
    with np.errstate(invalid='ignore', divide='ignore'):
        avg = tot / cnt
    avg[cnt == 0] = np.nan
    return avg

rng = np.random.default_rng(7)
bad = 0; nchecked = 0
for trial in range(120):
    nrow = 40
    m = int(rng.integers(1, 130))
    P = rng.normal(280, 4, size=(nrow, m))
    if rng.random() < 0.5:
        P = P.astype(np.float32).astype(np.float64)
    P = np.ascontiguousarray(P)
    keep = rng.random(size=(nrow, m)) < rng.uniform(0.0, 1.0)
    P[~keep] = np.nan
    if trial % 10 == 0: P[0] = np.nan
    if trial % 17 == 0: P[1, 0] = np.nan  # exactly one finite value
    mine_q = hazen_rows(P); mine_m = nanmean_rows(P)
    for r in range(nrow):
        nchecked += 1
        fin = np.isfinite(P[r])
        ref_q = np.quantile(P[r][fin], 0.9, method='hazen') if fin.any() else np.nan
        ref_m = np.nanmean(P[r]) if fin.any() else np.nan
        q_ok = (mine_q[r] == ref_q) if not np.isnan(ref_q) else np.isnan(mine_q[r])
        m_ok = (mine_m[r] == ref_m) if not np.isnan(ref_m) else np.isnan(mine_m[r])
        if not (q_ok and m_ok):
            bad += 1
            if bad < 6: print('MISMATCH t',trial,'r',r,'nv',int(fin.sum()), repr(mine_q[r]), repr(ref_q), repr(mine_m[r]), repr(ref_m))
print('validation: rows checked', nchecked, 'mismatches', bad)

# small-n direct checks
for n in [1,2,3,4,5,6,7,11,121,33]:
    for rep in range(30):
        vals = (rng.normal(285,2,size=(20,n))).astype(np.float32).astype(np.float64)
        mask = rng.random((20,n)) < 0.85
        P = np.where(mask, vals, np.nan)
        # ensure at least one finite
        P[:,0] = vals[:,0]
        mine = hazen_rows(P)
        ref = np.array([np.quantile(P[r][np.isfinite(P[r])],0.9,method='hazen') for r in range(20)])
        if not np.array_equal(mine, ref, equal_nan=True):
            print('small-n fail', n); break
print('small-n direct checks done')
