import numpy as np

X = np.load("/tmp/X.npy")
print("X shape:", X.shape)
sea = np.load("/tmp/sea.npy")
print("sea shape:", sea.shape, "sum:", int(sea.sum()))
Xsea = X[:, sea]
print("Xsea shape:", Xsea.shape)   # (4028, 3302)

# --- A) hazen: numpy definition h_i = (i+0.5)/n, p interpolates ---
def hazen_ref(x, p=0.9):
    x = np.sort(x); n = len(x)
    pos = n * p - 0.5           # 0-based
    i = int(np.floor(pos)); f = pos - i
    if i >= n - 1: return x[-1]
    return x[i] + f * (x[i+1] - x[i])
rng = np.random.default_rng(0)
ok = True
for n in [1, 2, 3, 7, 11, 33, 48, 121, 124, 131, 500]:
    for trial in range(20):
        x = rng.normal(285, 3, n)
        a = float(np.quantile(x, 0.9, method="hazen"))
        b = hazen_ref(x)
        if abs(a - b) > 1e-12 * max(1, abs(a)): ok = False; print("MISMATCH n=", n, a, b)
print("A) hazen quantile check:", "PASS" if ok else "FAIL")
