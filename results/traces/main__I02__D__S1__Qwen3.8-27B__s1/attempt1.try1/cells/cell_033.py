import numpy as np, datetime as dt
import warnings; warnings.filterwarnings('ignore')
S_tgt = np.load('/work/S_tgt.npy').reshape(92,-1)
thr_s = np.load('/work/thr_s.npy')
sea_cells = np.load('/work/sea_cells.npy')
tgt_doy = np.load('/work/tgt_doy.npy')
cr = np.load('/work/coords.npz')
tgt_dates = [dt.date.fromisoformat(str(d)) for d in cr['target_dates'].astype('datetime64[D]').astype(object)]

hot = S_tgt >= thr_s[tgt_doy]
sea_hot = hot[:, sea_cells]
print("per-day hot cell counts (max days):")
counts = sea_hot.sum(axis=1)
for i in range(92):
    if counts[i] > 0:
        print(" ", tgt_dates[i].isoformat(), int(counts[i]))
print("total hot cell-days:", int(sea_hot.sum()))
# longest hot streak per sea cell (to confirm none reach 5)
maxstreak = np.zeros(len(sea_cells), dtype=int)
for k in range(len(sea_cells)):
    h = sea_hot[:, k]; best = cur = 0
    for v in h:
        cur = cur+1 if v else 0
        best = max(best, cur)
    maxstreak[k] = best
print("max consecutive hot days over all sea cells:", int(maxstreak.max()))
mhw = np.load('/work/mhw_bool.npy')
print("mhw all zero:", bool((~mhw).all()), "shape:", mhw.shape)
active = np.load('/work/active.npy')
print("active all zero:", bool((~active).all()))
