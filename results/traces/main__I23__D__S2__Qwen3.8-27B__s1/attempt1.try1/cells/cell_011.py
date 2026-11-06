import numpy as np
import pickle

with open('/work/thr.pkl','rb') as f:
    T = pickle.load(f)
thr, clim = T['thr'], T['clim']
sea2 = T['sea2']; doy_tgt = T['doy_tgt']; V_tgt = T['V_tgt']
time_tgt = T['time_tgt']; lat = T['lat']; lon = T['lon']
K = thr.shape[1]

# confirm only row 60 is all-NaN before fill
nanrows = np.isnan(thr[1:]).all(axis=1)
print("rows all-NaN (idx in 1..366):", [i+1 for i in range(366) if nanrows[i]])

# day 60 = mean of 59 and 61
thr[60] = 0.5*(thr[59] + thr[61])
clim[60] = 0.5*(clim[59] + clim[61])
assert not np.isnan(thr[1:]).any() and not np.isnan(clim[1:]).any()

# 31-day centred moving mean, wrapping over 366 days
def smooth366(A):  # A shape (367, K), use rows 1..366
    B = A[1:].T                      # (K, 366)
    pad = np.concatenate([B[:, -15:], B, B[:, :15]], axis=1)  # (K, 396)
    S = pad.reshape(K, 366, 31).mean(axis=2)                  # (K, 366)
    return np.vstack([np.zeros((1, K)), S.T])

thr_s = smooth366(thr)
clim_s = smooth366(clim)
print("smoothed ok; doy60 thr before/after: %.4f %.4f" % (0.5*(thr[59]+thr[61]).mean(), thr_s[60].mean()))
# check wrap correctness on a synthetic series
A = np.zeros((367,1)); A[1:] = np.arange(366)
S = smooth366(A)[1:]
# day 366 should average days 351..366, 1..15 (0-indexed 350..365, 0..14)
exp = (np.arange(350,366) + np.arange(0,15)).mean()
print("wrap check day366:", S[365,0], "expected:", exp)
exp0 = (np.arange(0,16) + np.arange(351,366)).mean()
print("wrap check day1:", S[0,0], "expected:", exp0)

# ---- hot days: SST (kelvin, float64) >= threshold for that doy ----
SST = V_tgt.reshape(92, 3600)
hot = SST.T >= thr_s[doy_tgt]        # (3600, 92); land cells have NaN SST -> False
print("hot fraction sea cells:", hot[sea2].mean(), "| any hot on land:", bool(hot[~sea2].any()))

# ---- per-cell MHW: runs >=5 hot, join gaps of 1-2 non-hot days ----
mask = np.zeros((3600, 92), dtype=bool)
def runs_of(vec):
    idx = np.flatnonzero(vec)
    if idx.size == 0: return []
    brk = np.where(np.diff(idx) > 1)[0]
    starts = np.r_[idx[0], idx[brk+1]]
    ends = np.r_[idx[brk], idx[-1]]
    return list(zip(starts, ends))

t0=__import__('time').time()
n_merged = 0
for c in np.flatnonzero(sea2):
    h = hot[c]
    rs = [(s,e) for s,e in runs_of(h) if e-s+1 >= 5]
    merged = []
    for s,e in rs:
        if merged and s - merged[-1][1] - 1 <= 2:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s,e))
    if len(merged) > 1: n_merged += 1
    for s,e in merged:
        mask[c, s:e+1] = True
print("cell MHW done in %.1fs; cells with >1 merged block: %d" % (__import__('time').time()-t0, n_merged))

mask_out = (mask & sea2[:,None]).astype(np.uint8)
print("mask ones total:", int(mask_out.sum()))

# ---- regional events: maximal runs of active days ----
active = mask_out.any(axis=0)
ar = runs_of(active)
events = [(str(np.datetime_as_string(time_tgt[s], unit='D')),
           str(np.datetime_as_string(time_tgt[e], unit='D'))) for s,e in ar]
print("active days:", int(active.sum()), "of 92")
print("regional events:", events)
for s,e in ar:
    print("  event", str(np.datetime_as_string(time_tgt[s],unit='D')), "->", str(np.datetime_as_string(time_tgt[e],unit='D')), "len", e-s+1)

with open('/work/final.pkl','wb') as f:
    pickle.dump({'mask': mask_out, 'events': events, 'time_tgt': time_tgt,
                 'lat': lat, 'lon': lon, 'thr_s': thr_s, 'clim_s': clim_s,
                 'sea2': sea2, 'active': active}, f)
print("saved")
