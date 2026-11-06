import numpy as np, time
def smooth31(A):
    ext = np.concatenate([A, A, A], axis=0)
    C = np.empty((1099, A.shape[1]), dtype=np.float64)
    C[0] = 0.0
    np.cumsum(ext, axis=0, out=C[1:])
    s0 = 366 - 15
    return (C[s0+31 : s0+31+366] - C[s0 : s0+366]) / 31.0

rng = np.random.default_rng(7)
A = rng.random((366, 50))
S = smooth31(A)
# brute force
maxerr = 0
for i in range(366):
    idx = [(i + k) % 366 for k in range(-15, 16)]
    ref = A[idx].mean(axis=0)
    maxerr = max(maxerr, np.abs(S[i]-ref).max())
print("max abs err vs brute force:", maxerr)
assert maxerr < 1e-9
print("smooth31 verified against brute force")
