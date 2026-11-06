import numpy as np, pickle
from numpy.lib.stride_tricks import sliding_window_view

M = np.load("/tmp/M.npy")
with open("/tmp/sst_data.pkl","rb") as f: D = pickle.load(f)
sst_pool = D["sst_pool"]; sea = D["sea"]

cell_idx = np.where(sea)[0]
nc = len(cell_idx)
N = 4028
pool2 = sst_pool.reshape(N, 3600)[:, cell_idx]   # (N, nc)

# sanity: hazen via nanquantile matches manual HF type-5 (numpy convention)
vals = pool2[M[152], 0]
q_test = np.nanquantile(vals, 0.9, method="hazen")
xs = np.sort(vals); n = len(xs)
v = n*0.9 - 0.5
i = int(np.floor(v)); frac = v - i
manual = xs[i] + frac*(xs[i+1]-xs[i])
print("nanquantile hazen:", q_test, "manual:", manual, "match:", np.isclose(q_test, manual))
print("in C:", q_test-273.15)

thr = np.full((366, nc), np.nan)
clim = np.full((366, nc), np.nan)
for d in range(1, 367):
    if d == 60: continue
    X = pool2[M[d-1], :]
    thr[d-1] = np.nanquantile(X, 0.9, axis=0, method="hazen")
    clim[d-1] = np.nanmean(X, axis=0)

thr[59] = 0.5*(thr[58] + thr[60])
clim[59] = 0.5*(clim[58] + clim[60])
print("nan thr:", np.isnan(thr).any(), "nan clim:", np.isnan(clim).any())
# threshold >= climatology should hold everywhere (90pct >= mean)
print("thr < clim anywhere?", bool((thr < clim).any()))

def smooth31_wrap(a):
    b = np.concatenate([a[-15:], a, a[:15]], axis=0)
    return sliding_window_view(b, 31, axis=0).mean(axis=-1)

thr_s = smooth31_wrap(thr)
clim_s = smooth31_wrap(clim)
print("thr_s nan:", np.isnan(thr_s).any())

# explicit-loop smoothing check
rng = np.random.default_rng(2)
a = rng.standard_normal((366, 5)); s = smooth31_wrap(a)
ok = all(np.allclose(s[d], a[[(d+k)%366 for k in range(-15,16)]].mean(axis=0)) for d in range(366))
print("smoothing check:", ok)

print("thr_s day153 (Jun1) median C:", np.median(thr_s[152])-273.15)
print("clim_s day153 median C:", np.median(clim_s[152])-273.15)
print("thr_s range C:", thr_s.min()-273.15, thr_s.max()-273.15)
print("thr_s day244 (Aug31) median C:", np.median(thr_s[243])-273.15)

with open("/tmp/thr.pkl","wb") as f:
    pickle.dump({"thr": thr, "clim": clim, "thr_s": thr_s, "clim_s": clim_s, "cell_idx": cell_idx}, f)
print("saved")
