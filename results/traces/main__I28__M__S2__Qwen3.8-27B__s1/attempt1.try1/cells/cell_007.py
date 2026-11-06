import numpy as np, pickle

M = np.load("/tmp/M.npy")
with open("/tmp/sst_data.pkl","rb") as f: D = pickle.load(f)
sst_pool = D["sst_pool"]; sst_target = D["sst_target"]; sea = D["sea"]
print("numpy:", np.__version__)

# validate hazen vs manual HF type 5
rng = np.random.default_rng(0)
x = rng.standard_normal(121)
q_np = np.quantile(x, 0.9, method="hazen")
xs = np.sort(x)
n = len(xs)
h = (n+1)*0.9 - 0.5          # 1-indexed virtual position
i = int(np.floor(h)); frac = h - i
q_manual = xs[i-1] + frac*(xs[i]-xs[i-1]) if i < n else xs[-1]
print("hazen:", q_np, "manual:", q_manual, "match:", np.isclose(q_np, q_manual))

cell_idx = np.where(sea)[0]
nc = len(cell_idx)
print("sea cells:", nc)

pool2 = sst_pool[:, cell_idx, :].T   # (N, nc)
N = pool2.shape[0]

thr = np.full((366, nc), np.nan)
clim = np.full((366, nc), np.nan)
for d in range(1, 367):
    if d == 60: continue
    m = M[d-1]
    X = pool2[m, :]
    thr[d-1] = np.nanpercentile(X, 0.9, axis=0, method="hazen")
    clim[d-1] = np.nanmean(X, axis=0)

thr[59] = 0.5*(thr[58] + thr[60])
clim[59] = 0.5*(clim[58] + clim[60])

def smooth31_wrap(a):  # a: (366, ...) -> 31-day centred wrap mean
    b = np.concatenate([a[-15:], a, a[:15]], axis=0)
    from numpy.lib.stride_tricks import sliding_window_view
    return sliding_window_view(b, 31, axis=0).mean(axis=-1)

thr_s = smooth31_wrap(thr)
clim_s = smooth31_wrap(clim)
print("thr_s shape:", thr_s.shape, "any nan:", np.isnan(thr_s).any(), "clim nan:", np.isnan(clim_s).any())

# sanity: summer threshold in K
print("thr_s day153 (Jun1) median K:", np.nanmedian(thr_s[152]), "-> C:", np.nanmedian(thr_s[152])-273.15)
print("clim_s day153 median C:", np.nanmedian(clim_s[152])-273.15)
print("thr_s day60 equals mean(59,61) pre-smooth? spot:", thr[59,0] == 0.5*(thr[58,0]+thr[60,0]))

with open("/tmp/thr.pkl","wb") as f:
    pickle.dump({"thr": thr, "clim": clim, "thr_s": thr_s, "clim_s": clim_s,
                 "cell_idx": cell_idx, "sea": sea}, f)
print("saved")
