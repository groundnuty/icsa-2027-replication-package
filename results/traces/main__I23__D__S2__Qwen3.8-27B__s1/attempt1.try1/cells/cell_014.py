import numpy as np
import pickle

with open('/work/thr.pkl','rb') as f:
    T = pickle.load(f)
thr, clim = T['thr'], T['clim']
sea2 = T['sea2']; doy_tgt = T['doy_tgt']; V_tgt = T['V_tgt']
time_tgt = T['time_tgt']; lat = T['lat']; lon = T['lon']
K = thr.shape[1]

thr[60] = 0.5*(thr[59] + thr[61])
clim[60] = 0.5*(clim[59] + clim[61])
assert not np.isnan(thr[1:]).any() and not np.isnan(clim[1:]).any()

from numpy.lib.stride_tricks import sliding_window_view
def smooth366(A):  # (367, K), rows 1..366
    B = A[1:].T                                    # (K, 366)
    pad = np.concatenate([B[:, -15:], B, B[:, :15]], axis=1)
    S = sliding_window_view(pad, 31, axis=1).mean(axis=2)   # (K, 366)
    return np.vstack([np.zeros((1, B.shape[0])), S.T])

thr_s = smooth366(thr)
clim_s = smooth366(clim)

# wrap correctness check
A = np.zeros((367,1)); A[1:] = np.arange(366, dtype=float).reshape(-1,1)
S = smooth366(A)[1:, 0]
exp366 = (np.arange(350,366) + np.arange(0,15)).mean()
exp1   = (np.arange(0,16) + np.arange(351,366)).mean()
exp101 = np.arange(85,116).mean()
print("wrap checks: day366 %.4f/%.4f  day1 %.4f/%.4f  day101 %.4f/%.4f" %
      (S[365], exp366, S[0], exp1, S[100], exp101))
assert np.isclose(S[365], exp366) and np.isclose(S[0], exp1) and np.isclose(S[100], exp101)

SST = V_tgt.reshape(92, 3600)
hot = SST.T >= thr_s[doy_tgt]          # (3600, 92)
print("hot fraction (sea cells): %.4f | hot on land cells: %d" % (hot[sea2].mean(), int(hot[~sea2].sum())))

mask = np.zeros((3600, 92), dtype=bool)
def runs_of(vec):
    idx = np.flatnonzero(vec)
    if idx.size == 0: return []
    brk = np.where(np.diff(idx) > 1)[0]
    starts = np.r_[idx[0], idx[brk+1]]
    ends = np.r_[idx[brk], idx[-1]]
    return list(zip(starts.tolist(), ends.tolist()))

import time as _time
t0=_time.time()
tot_runs, tot_merged = 0, 0
for c in np.flatnonzero(sea2):
    rs = [(s,e) for s,e in runs_of(hot[c]) if e-s+1 >= 5]
    tot_runs += len(rs)
    merged = []
    for s,e in rs:
        if merged and s - merged[-1][1] - 1 <= 2:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s,e))
    tot_merged += len(merged)
    for s,e in merged:
        mask[c, s:e+1] = True
print("MHW done in %.1fs; >=5-day runs: %d, after joining: %d" % (_time.time()-t0, tot_runs, tot_merged))

mask_out = (mask & sea2[:,None]).astype(np.uint8)
print("mask ones:", int(mask_out.sum()))

active = mask_out.any(axis=0)
ar = runs_of(active)
events = [(str(np.datetime_as_string(time_tgt[s], unit='D')),
           str(np.datetime_as_string(time_tgt[e], unit='D'))) for s,e in ar]
print("active days:", int(active.sum()), "of 92; events:")
for (s,e),ev in zip(ar, events):
    print("  ", ev[0], "->", ev[1], "len", e-s+1)

with open('/work/final.pkl','wb') as f:
    pickle.dump({'mask': mask_out, 'events': events, 'time_tgt': time_tgt,
                 'lat': lat, 'lon': lon, 'sea2': sea2, 'active': active,
                 'thr_s': thr_s, 'clim_s': clim_s}, f)
print("saved")
