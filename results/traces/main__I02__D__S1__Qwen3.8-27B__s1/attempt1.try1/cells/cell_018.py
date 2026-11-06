import numpy as np
thr_s = np.load('/work/thr_s.npy'); clim_s = np.load('/work/clim_s.npy')
sea_cells = np.load('/work/sea_cells.npy'); tgt_doy = np.load('/work/tgt_doy.npy')
NC = thr_s.shape[1]
td = np.unique(tgt_doy)
print("target doys:", td.min(), "-", td.max())
nanpost = ~np.isfinite(thr_s)
# per sea cell: count NaN doys overall and within target range
cnt_all = nanpost.sum(axis=0)
cnt_tgt = np.zeros(NC, dtype=int)
for c in sea_cells:
    cnt_tgt[c] = nanpost[td, c].sum()
sea = set(sea_cells.tolist())
print("sea cells with ANY NaN thr (any day):", sum(1 for c in sea if cnt_all[c] > 0))
print("sea cells with NaN on any TARGET doy:", int((cnt_tgt[list(sea)] > 0).sum()))
bad = [c for c in sea if cnt_tgt[c] > 0]
print("those cells:", bad[:30])
if bad:
    for c in bad[:5]:
        nds = [d for d in range(366) if nanpost[d, c]]
        print("cell", c, "NaN doys:", nds[:40], "n=", len(nds))
# clim NaN audit
nc_nan = (~np.isfinite(clim_s)).sum(axis=0)
print("sea cells with NaN clim on target doys:", int((np.array([ (~np.isfinite(clim_s[td, c])).any() for c in sea])).sum()))
