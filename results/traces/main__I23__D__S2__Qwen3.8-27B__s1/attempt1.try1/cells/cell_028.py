import numpy as np
import pickle

with open('/work/final.pkl','rb') as f:
    F = pickle.load(f)
with open('/work/thr.pkl','rb') as f:
    T = pickle.load(f)
mask, time_tgt, sea2 = F['mask'], F['time_tgt'], F['sea2']
c = 665
sea_order = np.flatnonzero(sea2)
k = int(np.searchsorted(sea_order, c))
V = T['V_tgt'].reshape(92,3600)
th_s = F['thr_s'][T['doy_tgt'], :][:, k]
print("cell (57.64, 18.80):  date       SST     thr_s    hot?")
for d in range(4, 16):
    print("  ", str(np.datetime64(time_tgt[d],'D')), "%.2f" % V[d,c], "%.2f" % th_s[d], bool(V[d,c] >= th_s[d]))

SST_sea = T['V_tgt'].reshape(92,3600)[:, sea2].T
hot = SST_sea >= F['thr_s'][T['doy_tgt']].T
best = {}
for kk in range(hot.shape[0]):
    idx = np.flatnonzero(hot[kk])
    if idx.size == 0: continue
    brk = np.where(np.diff(idx) > 1)[0]
    starts = np.r_[idx[0], idx[brk+1]]
    ends = np.r_[idx[brk], idx[-1]]
    for s,e in zip(starts, ends):
        best.setdefault(e-s+1, []).append((kk, int(s), int(e)))
print("hot-run lengths present:")
for L in sorted(best, reverse=True)[:6]:
    ex = best[L][:3]
    print("  len", L, "count", len(best[L]), "e.g. (cellk, start, end):", ex)
