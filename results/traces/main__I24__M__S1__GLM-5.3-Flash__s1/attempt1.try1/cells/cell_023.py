import numpy as np

def hazen_rows(P):
    fin = np.isfinite(P)
    nv = fin.sum(axis=1)
    S = np.sort(np.where(fin, P, np.inf), axis=1)
    n = nv.astype(np.float64)
    virtual = n*0.9 + (0.5 + 0.9*(1 - 0.5 - 0.5)) - 1.0
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
    gamma = virtual - previous.astype(np.float64)
    rows = np.arange(P.shape[0])
    a = S[rows, previous]
    b = S[rows, nxt]
    diff_b_a = b - a
    l = a + diff_b_a * gamma
    l = np.where(gamma >= 0.5, b - diff_b_a*(1 - gamma), l)
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
for trial in range(80):
    nrow = 40
    m = int(rng.integers(1, 130))
    P = rng.normal(280, 4, size=(nrow, m))
    if rng.random() < 0.5:
        P = P.astype(np.float32).astype(np.float64)
    P = np.ascontiguousarray(P)
    keep = rng.random(size=(nrow, m)) < rng.uniform(0.3, 1.0)
    P[~keep] = np.nan
    if trial % 10 == 0: P[0] = np.nan
    if trial % 17 == 0: P[1, 0] = np.nan  # single-value row
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
