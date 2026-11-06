import numpy as np, h5py, time, os
p = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"

# verify nanquantile hazen == per-column quantile of finite values (type 5)
rng = np.random.default_rng(1)
A = rng.normal(size=(200, 7))
mask = rng.random((200,7)) < 0.15
A[mask] = np.nan
A[3, 5] = np.nan  # extra
ref = np.array([np.quantile(col[np.isfinite(col)], 0.9, method="hazen") if np.isfinite(col).any() else np.nan for col in A.T])
got = np.nanquantile(A, 0.9, axis=0, method="hazen")
print("nanquantile==percol:", np.allclose(ref, got, equal_nan=True))
# all-nan column
B = A.copy(); B[:, 6] = np.nan
import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    g2 = np.nanquantile(B, 0.9, axis=0, method="hazen")
print("all-nan col -> nan:", np.isnan(g2[6]), "others ok:", np.allclose(g2[:6], got[:6]))

# timing: 100-day batch read of region
t0 = time.time()
f = h5py.File(p, "r")
d = f["analysed_sst"]
r = d[200:300, 182:242, 690:750]
t1 = time.time()
print("100 days:", round(t1-t0,2), "s")
r2 = d[3000:3100, 182:242, 690:750]
t2 = time.time()
print("100 more (later):", round(t2-t1,2), "s")
f.close()
print("/work writable:", os.access("/work", os.W_OK))
