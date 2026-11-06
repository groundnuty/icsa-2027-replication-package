import numpy as np, pickle
from numpy.lib.stride_tricks import sliding_window_view

M = np.load("/tmp/M.npy")
with open("/tmp/sst_data.pkl","rb") as f: D = pickle.load(f)
sst_pool = D["sst_pool"]; sst_target = D["sst_target"]; sea = D["sea"]

# correct manual HF type 5 check: h1 = (n+1)p + 0.5 (1-indexed)
rng = np.random.default_rng(0)
x = rng.standard_normal(121)
q_np = np.quantile(x, 0.9, method="hazen")
xs = np.sort(x); n = len(xs)
h1 = (n+1)*0.9 + 0.5
i = int(np.floor(h1)); frac = h1 - i
q_manual = xs[i-1] + frac*(xs[i]-xs[i-1])
print("hazen:", q_np, "manual:", q_manual, "match:", np.isclose(q_np, q_manual))
# also compare against MATLAB-style: MATLAB quantile default for n>1 is linear type 7 (for reference)
q_matlab_default = np.quantile(x, 0.9, method="linear")
print("(reference) type7:", q_matlab_default)

cell_idx = np.where(sea)[0]
nc = len(cell_idx)
N = 4028
pool2 = sst_pool.reshape(N, 3600)[:, cell_idx].T   # (N, nc)

thr = np.full((366, nc), np.nan)
clim = np.full((366, nc), np.nan)
for d in range(1, 367):
    if d == 60: continue
    X = pool2[M[d-1], :]
    thr[d-1] = np.nanpercentile(X, 0.9, axis=0, method="hazen")
    clim[d-1] = np.nanmean(X, axis=0)

thr[59] = 0.5*(thr[58] + thr[60])
clim[59] = 0.5*(clim[58] + clim[60])
print("nan thr:", np.isnan(thr).any(), "nan clim:", np.isnan(clim).any())

def smooth31_wrap(a):
    b = np.concatenate([a[-15:], a, a[:15]], axis=0)
    return sliding_window_view(b, 31, axis=0).mean(axis=-1)

thr_s = smooth31_wrap(thr)
clim_s = smooth31_wrap(clim)
print("thr_s nan:", np.isnan(thr_s).any(), "clim_s nan:", np.isnan(clim_s).any())

# sanity: verify smoothing at wrap boundary d=1: mean of days 352..366,1..15 (i.e. rows 351..365,0..14 0-based)
manual = np.concatenate([thr[351:], thr[:15]], axis=0).mean(axis=0)
print("wrap check day1 match:", np.allclose(thr_s[0], manual))
manual2 = thr[100:131].mean(axis=0)
print("mid check day116 match:", np.allclose(thr_s[115], manual2))

print("thr_s day153 median C:", np.nanmedian(thr_s[152])-273.15)
print("clim_s day153 median C:", np.nanmedian(clim_s[152])-273.15)
print("thr min/max C:", thr_s.min()-273.15, thr_s.max()-273.15)

with open("/tmp/thr.pkl","wb") as f:
    pickle.dump({"thr": thr, "clim": clim, "thr_s": thr_s, "clim_s": clim_s, "cell_idx": cell_idx}, f)
print("saved")
