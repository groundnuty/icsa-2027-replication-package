import numpy as np, pickle, time
X = np.load("/tmp/X.npy")
pools = pickle.load(open("/tmp/pools.pkl","rb"))["pools"]
Nc = 3600
Xd = X.reshape(4028, Nc)

def hazen90(pool):
    # pool: (121, Nc) float64, may contain NaN
    S = np.sort(pool, axis=0)                      # NaNs sort last
    nv = 121 - np.isnan(pool).sum(axis=0)          # valid counts (Nc,)
    j = 0.9*nv - 0.5                               # 0-based virtual index (HF type 5: h1 = 0.9*nv+0.5)
    jf = np.floor(j).astype(np.int64)
    jc = np.minimum(jf+1, 120)
    # clamp jf to [0,120]; for nv==0 jf=-1 -> maps to NaN slot (last is NaN)
    jf = np.clip(jf, 0, 120)
    frac = j - jf
    a = np.take_along_axis(S, jf[None,:], axis=0)[0]
    b = np.take_along_axis(S, jc[None,:], axis=0)[0]
    val = a + frac*(b-a)
    val = np.where(nv > 0, val, np.nan)
    return val

# cross-validate vs numpy nanquantile on random pools
rng = np.random.default_rng(0)
ok = True
for trial in range(30):
    p = rng.normal(285, 2, (121, 50)).astype("float64")
    m = rng.random((121,50)) < rng.uniform(0, 0.5)
    p[m] = np.nan
    ref = np.array([np.nanquantile(p[:,k], 0.9, method="hazen") for k in range(50)])
    got = hazen90(p)
    if not np.allclose(ref, got, equal_nan=True, rtol=1e-12, atol=1e-12):
        ok = False
        print("MISMATCH", trial, ref[:5], got[:5])
        break
print("cross-validation:", "PASS" if ok else "FAIL")
