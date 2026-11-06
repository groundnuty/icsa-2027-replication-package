import numpy as np
# Verify hazen quantile implementation against numpy
rng = np.random.default_rng(42)
for trial in range(5):
    n = rng.integers(5, 200)
    a = rng.normal(size=n)
    # my implementation
    s = np.sort(a)
    p = 0.9
    h = n * p + 0.5
    lo = int(np.floor(h)) - 1
    frac = h - np.floor(h)
    q = s[lo] + frac * (s[lo+1] - s[lo])
    ref = np.quantile(a, p, method="hazen")
    assert np.isclose(q, ref), (q, ref)
print("hazen implementation matches np.quantile(method='hazen')")

# Verify my vectorized per-cell version (handles per-cell NaN counts) on synthetic 3D
v = rng.normal(size=(121, 4, 4))
v[0, 0, 0] = np.nan; v[1, 0, 0] = np.nan  # cell (0,0) has 119 valid
s = np.sort(v, axis=0)
nn = np.sum(~np.isnan(v), axis=0)
with np.errstate(invalid="ignore"):
    h = nn * 0.9 + 0.5
h = np.where(nn > 0, h, np.nan)
lo_i = np.floor(h).astype(int) - 1
frac = h - np.floor(h)
lo_i_c = np.clip(lo_i, 0, v.shape[0]-1)
hi_i_c = np.clip(lo_i+1, 0, v.shape[0]-1)
v_lo = np.take_along_axis(s, lo_i_c[None], axis=0)[0]
v_hi = np.take_along_axis(s, hi_i_c[None], axis=0)[0]
q = v_lo + frac * (v_hi - v_lo)
q = np.where(nn > 0, q, np.nan)
# compare per cell
for i in range(4):
    for j in range(4):
        col = v[:, i, j]
        col = col[~np.isnan(col)]
        if len(col) == 0:
            assert np.isnan(q[i, j]); continue
        ref = np.quantile(col, 0.9, method="hazen")
        assert np.isclose(q[i, j], ref), (i, j, q[i,j], ref)
print("vectorized per-cell hazen OK (handles per-cell NaN counts)")
