import numpy as np
import pickle

with open('/work/final.pkl','rb') as f:
    F = pickle.load(f)
with open('/work/thr.pkl','rb') as f:
    T = pickle.load(f)
mask, time_tgt = F['mask'], F['time_tgt']
ones = np.argwhere(mask == 1)
print("mask-1 cells (flat):", np.unique(ones[:,0]), "days:", [str(np.datetime64(time_tgt[d],'D')) for d in np.unique(ones[:,1])])
c = ones[0,0]
lati, loni = np.unravel_index(c, (60,60))
print("cell lat/lon: %.4f %.4f" % (57.42+0.02*lati, 18.70+0.02*loni))
V = T['V_tgt'].reshape(92,3600)
th_s = F['thr_s'][T['doy_tgt']]
print(" date       SST     thr_s    hot?")
for d in range(4, 16):
    print("  ", str(np.datetime64(time_tgt[d],'D')), "%.2f" % V[d,c], "%.2f" % th_s[d], bool(V[d,c] >= th_s[d]))

# also verify no other near-miss: longest hot run among sea cells not in an MHW
sea2 = F['sea2']
SST_sea = T['V_tgt'].reshape(92,3600)[:, sea2].T
hot = SST_sea >= th_s.T
best = {}
for k in range(hot.shape[0]):
    idx = np.flatnonzero(hot[k])
    if idx.size == 0: continue
    brk = np.where(np.diff(idx) > 1)[0]
    starts = np.r_[idx[0], idx[brk+1]]
    ends = np.r_[idx[brk], idx[-1]]
    for s,e in zip(starts, ends):
        L = e-s+1
        if L >= 3:
            best.setdefault(L, []).append((k, s, e))
for L in sorted(best, reverse=True):
    print("hot run len", L, ": e.g.", best[L][:3])
