import numpy as np, pickle
from datetime import date

with open('/work/dates.pkl','rb') as f: dd = pickle.load(f)
tgt_dates = dd['tgt']; nb = len(dd['base'])
SST = np.load('/work/SST_all.npy')
sea = np.load('/work/sea_mask.npy').ravel()
thr_s = np.load('/work/thr_smooth.npy')
mhw = np.load('/work/mhw.npy')

def mdoy(dt): return (date(2000, dt.month, dt.day) - date(2000,1,1)).days + 1
doys = np.array([mdoy(d) for d in tgt_dates])
tgt = SST[nb:].reshape(len(tgt_dates), 3600)
hot = (tgt >= thr_s[doys - 1]) & sea[np.newaxis, :]

active = mhw.any(axis=1)
print("day | active_cells | hot_cells")
for i, d in enumerate(tgt_dates):
    print(d.isoformat(), int(active[i]*1 and mhw[i].sum()) or 0, int(hot[i].sum()), end="  ")
    if (i+1) % 6 == 0: print()
print()
# event boundaries
act_idx = np.where(active)[0]
print("active day range:", tgt_dates[act_idx.min()], "->", tgt_dates[act_idx.max()])
# check gap between events: June 17-19 inactive
for i in [14,15,16,17,18,19]:
    print(tgt_dates[i], "active:", bool(active[i]), "mhw cells:", int(mhw[i].sum()), "hot cells:", int(hot[i].sum()))
# August: max excess of SST over threshold
aug = slice(72, 92)  # Aug 1..20 (Jun1=0 => Aug1=72)
exc = tgt[aug] - thr_s[doys[aug]-1]
print("Aug max daily excess (K):", exc.max(), "on", tgt_dates[72 + int(np.argmax(exc.max(axis=1)))])
daily_max_exc = exc.max(axis=1)
print("Aug daily max excess:", np.round(daily_max_exc, 2))
