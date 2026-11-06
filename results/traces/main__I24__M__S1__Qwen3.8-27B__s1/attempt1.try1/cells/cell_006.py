import numpy as np

rng = np.random.default_rng(0)

def hazen_ref(v, q=0.9):
    v = np.asarray(v, dtype=np.float64)
    if v.size == 0: return np.nan
    return np.quantile(v, q, method="hazen")

def hazen_fast(v, q=0.9):
    """v 1-D with possible NaNs; return hazen quantile ignoring NaN. NaN if all NaN."""
    v = np.asarray(v, dtype=np.float64)
    nn = np.isfinite(v)  # NaN check; no infs expected
    n = nn.sum()
    if n == 0: return np.nan
    vv = np.where(nn, v, np.inf)
    s = np.sort(vv)
    # determine numpy hazen formula
    return _hazen(s, n, q)

def _hazen(s, n, q):
    # candidate: h0 = (n+1)*q - 1.5  (Hyndman-Fan type 5)
    h0 = (n + 1) * q - 0.5
    i = int(np.floor(h0)); g = h0 - i
    if i >= n - 1 or g == 0:
        return s[min(i, n-1)]
    return s[i] + g * (s[i+1] - s[i])

# test formula against numpy
ok = True
for trial in range(2000):
    n = int(rng.integers(1, 60))
    v = rng.random(n)
    r = hazen_ref(v)
    f = _hazen(np.sort(v), n, 0.9)
    if not np.isclose(r, f, rtol=0, atol=1e-12):
        ok = False
        print("MISMATCH n=", n, "numpy:", r, "hf5:", f, v)
        break
print("HF type5 formula matches numpy 'hazen':", ok)

# also compare with 'linear' to confirm they differ
v = np.arange(21, dtype=float)
print("n=21 arange: hazen:", np.quantile(v, 0.9, method='hazen'),
      "linear:", np.quantile(v, 0.9, method='linear'),
      "hf5 manual:", 10*0.9-1.5+10*0)  # placeholder
