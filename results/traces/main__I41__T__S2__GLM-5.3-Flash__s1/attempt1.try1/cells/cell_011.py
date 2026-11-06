import numpy as np, time

# --- validate manual hazen percentile vs np.nanpercentile(method='hazen') ---
rng = np.random.default_rng(42)
x = np.array([1.,2.,3.,4.,5.])
print("hazen check [1..5] p90:", np.percentile(x, 90, method='hazen'), "(expect 4.6)")
print("hazen check [1,2,3,4] p25:", np.percentile(x[:4], 25, method='hazen'), "(expect 1.75)")

def hazen_percentile(pool, p=0.90):
    """pool: (n, ...) with NaNs; returns hazen percentile along axis 0, ignoring NaN."""
    n_max = pool.shape[0]
    counts = (~np.isnan(pool)).sum(axis=0)
    xs = np.sort(pool, axis=0)  # NaNs at the end
    vi = p * (counts - 1.0)                       # 0-based virtual index
    lo = np.floor(vi).astype(np.int64)
    gamma = vi - lo
    lo_c = np.clip(lo, 0, n_max - 1)
    hi_c = np.clip(lo + 1, 0, n_max - 1)
    a = np.take_along_axis(xs, lo_c[None], axis=0)[0]
    b = np.take_along_axis(xs, hi_c[None], axis=0)[0]
    out = np.where(gamma == 0, a, a + gamma * (b - a))
    out = np.where(counts == 0, np.nan, out)
    return out

# random tests with NaNs
ok = True
for trial in range(5):
    n = rng.integers(1, 30)
    arr = rng.normal(size=(n, 7, 3))
    m = rng.random(arr.shape) < 0.3
    arr[m] = np.nan
    got = hazen_percentile(arr, 0.90)
    ref = np.nanpercentile(arr, 90, axis=0, method='hazen')
    both_nan = np.isnan(got) & np.isnan(ref)
    match = np.allclose(got[~both_nan], ref[~both_nan], rtol=0, atol=1e-12) and np.array_equal(both_nan, np.isnan(ref))
    if not match:
        ok = False
        print("MISMATCH trial", trial, np.nanmax(np.abs(got-ref)))
print("manual hazen vs np.nanpercentile:", "ALL MATCH" if ok else "ERRORS")
