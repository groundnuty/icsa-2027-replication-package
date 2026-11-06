import numpy as np

sea = np.load("/tmp/sea.npy")
mhw_flat = np.load("/tmp/final_mhw.npy")
X = np.load("/tmp/X.npy"); p3 = np.load("/tmp/p3.npy")

# 1) verify flattening order: X[:, sea] column c == X[:, li[c], oi[c]] ?
li, oi = np.where(sea)
Xsea = X[:, sea]
mism = 0
for c in [0, 1, 123, 400, 3301]:
    a = Xsea[:, c]
    b = X[:, li[c], oi[c]]
    same = np.array_equal(np.isnan(a), np.isnan(b)) and np.allclose(a[np.isfinite(a)], b[np.isfinite(b)])
    if not same: mism += 1
    print("c=%d mapping consistent: %s" % (c, same))
print("mapping mismatches:", mism)

# 2) for c=400, compare hot days stored vs recomputed
c = 400
row, colxy = divmod(c, 60)
print("c=400 -> row,col:", row, colxy, " sea:", sea[row, colxy])
print("stored col vs mapped col equal:", np.array_equal(Xsea[:, c], X[:, row, colxy]))
