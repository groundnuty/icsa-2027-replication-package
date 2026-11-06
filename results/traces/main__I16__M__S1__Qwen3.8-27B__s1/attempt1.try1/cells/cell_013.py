import numpy as np
B = np.load("/tmp/B.npy"); Xall = np.load("/tmp/Xall.npy")
X_b = Xall[:4028].reshape(4028, 3600)

# which cells have NaN pools?
nan_cells = []
for c in range(3600):
    if not np.all(np.isfinite(X_b[:, c])):
        # count finite per pool is what matters; check a specific pool
        pass
# check finiteness per cell across baseline window
fin = np.isfinite(X_b).mean(axis=0)
print("cells with <50% finite baseline:", (fin<0.5).sum(), "0 finite:", (fin==0).sum())
zero_cells = np.nonzero(fin==0)[0]
print("zero cells:", zero_cells[:10])

# debug quantile on one cell/day
c = int(rng_c := 0)
r = 0
P = X_b[B[r], c]
Pf = P[np.isfinite(P)]
print("n finite:", len(Pf))
S = np.sort(P)
n = len(Pf)
h = 1 + 0.9*(n-1); i = int(np.floor(h)); g = h-i
i0 = int(np.clip(i-1, 0, n-1))
lo = S[i0]; hi = S[min(i0+1, n-1)] if i0+1 < n else lo
mine = (1-g)*lo + g*hi
ref = np.quantile(Pf, 0.9, method="hazen")
print("h", h, "i", i, "g", g, "i0", i0)
print("mine", mine, "ref", ref, "S[i0],S[i0+1]", S[i0], S[i0+1] if i0+1<n else None)
