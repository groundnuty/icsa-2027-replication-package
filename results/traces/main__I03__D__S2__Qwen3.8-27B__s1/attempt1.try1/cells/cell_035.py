import numpy as np

def hazen90_cols(A):
    n = np.isfinite(A).sum(axis=0)
    S = np.sort(A, axis=0)
    out = np.full(A.shape[1], np.nan)
    ok = n > 0
    v = 0.9*n[ok] - 0.5
    vm = np.clip(v, 0.0, n[ok]-1)
    j = np.floor(vm).astype(np.int64)
    jj = np.clip(j+1, 0, n[ok]-1)
    g = vm - j
    cols = np.arange(n[ok].size)
    out[ok] = S[j, cols] + g*(S[jj, cols] - S[j, cols])
    return out, n

# minimal: all finite
A = np.arange(121*5, dtype=np.float64).reshape(121,5)
q, n = hazen90_cols(A)
print("all finite:", q, n)
# expected for col0: 0.9*121-0.5=108.4 -> x[108]+0.4*(x[109]-x[108]) = 108 + 0.4 = 108.4
# with NaN in one column
B = A.copy(); B[3, 2] = np.nan
q2, n2 = hazen90_cols(B)
print("one nan:", q2, n2)
import warnings
with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    print("ref:", np.nanquantile(B, 0.9, method='hazen', axis=0))
