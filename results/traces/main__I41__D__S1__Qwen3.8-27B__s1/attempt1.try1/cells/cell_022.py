import pickle, numpy as np
from datetime import date

with open('/work/dates.pkl','rb') as f: dd = pickle.load(f)
tgt_dates = dd['tgt']
nb = len(dd['base'])
SST = np.load('/work/SST_all.npy')
sea_mask = np.load('/work/sea_mask.npy').ravel()
thr_s = np.load('/work/thr_smooth.npy')

def mdoy(dt):
    return (date(2000, dt.month, dt.day) - date(2000,1,1)).days + 1

tgt = SST[nb:]
doys = np.array([mdoy(d) for d in tgt_dates])
print("target doy range:", doys.min(), doys.max(), "expected 153..244")
thr_t = thr_s[doys - 1]                      # (92, 3600)
hot = (tgt >= thr_t) & sea_mask[np.newaxis, :]
print("hot cell-days:", int(hot.sum()))

n_t = len(tgt_dates)
mhw = np.zeros((n_t, 3600), dtype=np.uint8)
for c in range(3600):
    h = hot[:, c]
    if not h.any(): continue
    d = np.diff(np.concatenate([[0], h.view(np.int8), [0]]))
    starts = np.where(d == 1)[0]
    ends = np.where(d == -1)[0] - 1
    runs = [(s, e) for s, e in zip(starts, ends) if (e - s + 1) >= 5]
    merged = []
    for s, e in runs:
        if merged and s - merged[-1][1] - 1 <= 2:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))
    for s, e in merged:
        mhw[s:e+1, c] = 1
np.save('/work/mhw.npy', mhw)
print("MHW cell-days (incl. gap days):", int(mhw.sum()))
print("cells with >=1 MHW:", int((mhw.sum(axis=0) > 0).sum()))

active = mhw.any(axis=1)
print("active days:", int(active.sum()), "of 92")
d = np.diff(np.concatenate([[0], active.view(np.int8), [0]]))
st = np.where(d == 1)[0]; en = np.where(d == -1)[0] - 1
ev = [(tgt_dates[s].isoformat(), tgt_dates[e].isoformat(), int(e - s + 1)) for s, e in zip(st, en)]
print("regional events:", len(ev))
for e in ev: print("  ", e)
pickle.dump(ev, open('/work/events.pkl','wb'))
pickle.dump(doys.tolist(), open('/work/doys.pkl','wb'))
