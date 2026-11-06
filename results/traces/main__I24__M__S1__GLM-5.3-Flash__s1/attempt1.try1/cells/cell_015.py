import numpy as np, time as time_mod

def hazen_rows(P):
    """Exact vectorized replication of np.quantile(row, 0.9, method='hazen') over finite values.
    P: (nrow, m) C-contiguous. Replicates numpy's _quantile arithmetic op-for-op."""
    fin = np.isfinite(P)
    nv = fin.sum(axis=1)
    S = np.sort(np.where(fin, P, np.inf), axis=1)
    n = nv.astype(np.float64)
    h = n*0.9 - 0.5                       # virtual index for hazen (alpha=beta=1/2)
    prev = np.floor(h).astype(np.int64)
    nxt = prev + 1
    above = h >= (nv - 1)                 # numpy: virtual_indexes >= arr.shape[axis]-1
    prev = np.where(above, -1, prev)
    nxt = np.where(above, -1, nxt)
    h2 = np.where(above, (nv-1).astype(np.float64), h)
    gamma = h2 - prev.astype(np.float64)  # numpy _get_gamma: virtual - previous
    rows = np.arange(P.shape[0])
    a = S[rows, prev]
    b = S[rows, nxt]
    diff_b_a = b - a                      # numpy _lerp, exact op order:
    l = a + diff_b_a * gamma
    l = np.where(gamma >= 0.5, b - diff_b_a*(1-gamma), l)
    l[nv == 0] = np.nan
    return l

def nanmean_rows(P):
    """Exact replication of np.nanmean(P, axis=1) (which copies, NaN->0, sums full row, divides by count)."""
    fin = np.isfinite(P)
    P0 = np.where(fin, P, 0.0)
    tot = P0.sum(axis=1)                  # same layout => same pairwise summation as nanmean
    cnt = fin.sum(axis=1)
    with np.errstate(invalid='ignore', divide='ignore'):
        avg = tot / cnt
    avg[cnt == 0] = np.nan
    return avg

# ---- bitwise validation ----
rng = np.random.default_rng(7)
bad = 0; nchecked = 0
for trial in range(60):
    nrow = 40
    m = int(rng.integers(1, 130))
    P = rng.normal(280, 4, size=(nrow, m))
    if rng.random() < 0.5:
        P = P.astype(np.float32).astype(np.float64)
    P = np.ascontiguousarray(P)
    keep = rng.random(size=(nrow, m)) < rng.uniform(0.5, 1.0)
    P[~keep] = np.nan
    if trial % 10 == 0: P[0] = np.nan  # all-NaN row
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
            if bad < 5: print('MISMATCH t',trial,'r',r,'nv',fin.sum(), repr(mine_q[r]), repr(ref_q), repr(mine_m[r]), repr(ref_m))
print('validation: rows checked', nchecked, 'mismatches', bad)
