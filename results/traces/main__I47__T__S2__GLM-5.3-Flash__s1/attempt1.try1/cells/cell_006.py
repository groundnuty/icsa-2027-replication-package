import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
rng = np.random.default_rng(7)

# ---- Empirically pin down numpy's 'hazen' virtual index ----
# sorted x = 0..n-1 -> returned value == virtual index (0-based) when no clipping
for n in (1, 2, 3, 5, 10, 121):
    x = np.arange(n, dtype=float)
    v_np = float(np.quantile(x, 0.9, method='hazen'))
    cands = {'A: 0.9n-0.5 (HF type5)': 0.9*n-0.5,
             'B: 0.9(n-1) (type7/linear)': 0.9*(n-1),
             'C: 0.9n-0.4': 0.9*n-0.4}
    print(f"n={n:4d} numpy hazen = {v_np:9.4f} | " +
          "  ".join(f"{k}={v:8.4f}{'*' if abs(v-v_np)<1e-12 else ''}" for k, v in cands.items()))

# ---- vectorized NaN-aware hazen, column-wise ----
def hazen_cols(P):
    s = np.sort(P, axis=0)
    n = np.count_nonzero(~np.isnan(P), axis=0)
    v = 0.9*n - 0.5
    lo = np.floor(v).astype(np.int64); frac = v - lo
    nmax = np.maximum(n-1, 0)
    lo_c = np.clip(lo, 0, nmax); hi_c = np.clip(lo+1, 0, nmax)
    cols = np.arange(P.shape[1])
    q = s[lo_c, cols] + frac*(s[hi_c, cols]-s[lo_c, cols])
    q[n == 0] = np.nan
    return q

for k in (3, 12, 121):
    P = rng.normal(size=(k, 500))
    P[rng.random(P.shape) < 0.3] = np.nan
    P[:5] = np.nan                      # some all-NaN columns
    q = hazen_cols(P)
    with np.errstate(all='ignore'):
        ref = np.nanquantile(P, 0.9, axis=0, method='hazen')
    same_nan = np.array_equal(np.isnan(q), np.isnan(ref))
    diff = np.nanmax(np.abs(q - ref)) if same_nan else np.inf
    print(f"k={k}: hazen vs numpy  max|diff|={diff:.3e}  nan-pattern match={same_nan}")

# mean check
P = rng.normal(size=(121, 500)); P[rng.random(P.shape) < 0.3] = np.nan
m = np.nanmean(P, axis=0)
print("nanmean matches np:", np.allclose(m, np.nanmean(P, axis=0)))

# ---- circular 31-day moving mean, column-wise ----
def circ31(x):  # x: (366, ncols)
    xp = np.concatenate([x[-15:], x, x[:15]], axis=0)
    return sliding_window_view(xp, 31, axis=0).mean(axis=-1)

X = rng.normal(size=(366, 7))
sm = circ31(X)
ref = np.stack([[X[(np.arange(d-15, d+16)) % 366, c].mean() for d in range(366)]
                for c in range(7)], axis=1)
print("circular smoothing max|diff|:", np.abs(sm-ref).max())

# day-60 fill check
raw = rng.normal(size=(366, 4)); raw[59] = np.nan
raw[59] = (raw[58] + raw[60]) / 2
print("day60 fill ok:", np.allclose(raw[59], (raw[58]+raw[60])/2))
print("VERIFICATION PASSED")
