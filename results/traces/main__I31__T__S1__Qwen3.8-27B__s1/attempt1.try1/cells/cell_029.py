
import numpy as np
H = (np.load('work/H2.npy') if True else None)
print("H2 loaded:", H.shape, H.dtype, "sum:", int(H.sum()))
d = np.diff(np.concatenate([np.zeros((1, H.shape[1]), bool), H, np.zeros((1, H.shape[1]), bool)], axis=0), axis=0)
print("d shape:", d.shape, "unique:", np.unique(d))
si = np.where(d == 1); ei = np.where(d == -1)
print("n +1:", si[0].size, " n -1:", ei[0].size)
# find columns where counts differ
import collections
c1 = collections.Counter(si[1].tolist())
c2 = collections.Counter(ei[1].tolist())
bad = [c for c in set(c1) | set(c2) if c1[c] != c2[c]]
print("cols with mismatch:", bad[:10])
if bad:
    c = bad[0]
    col = H[:, c]
    print("col", c, ":", col.astype(int).tolist())
    print("starts rows:", si[0][si[1]==c].tolist(), "ends rows:", ei[0][ei[1]==c].tolist())
