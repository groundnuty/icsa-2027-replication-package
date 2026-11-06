import numpy as np
m = np.load('/work/mask.npz')
mask = m['mask']; active = m['active']
tgt_dates = [d for d in m['tgt_dates']]
import datetime as dt
# print day-by-day: active, cells in MHW, cells hot
data = np.load('/work/S.npz', allow_pickle=True)
S_base = data['S_base']; S_tgt = data['S_tgt']
sea = np.isfinite(S_tgt).all(axis=0)
St = S_tgt[:, sea].astype(np.float64)
tc = np.load('/work/thrclim.npz')
THR_s = None
# recompute smoothing of THR quickly
def smooth366(arr):
    pad = np.concatenate([arr[-15:], arr, arr[:15]], axis=0)
    cs = np.concatenate([np.zeros((1, arr.shape[1])), np.cumsum(pad, axis=0)], axis=0)
    return (cs[31:] - cs[:-31]) / 31.0
THR = tc['THR']
def doy(d): return (d.replace(year=2020) - dt.date(2020,1,1)).days + 1
td = [dt.date.fromisoformat(s) for s in tgt_dates]
THR_t = smooth366(THR)[[doy(d)-1 for d in td]]
hot = St >= THR_t
print("day  n_hot  n_mhw  active")
for i in range(92):
    print(tgt_dates[i], int(hot[i].sum()), int(mask[i].sum()), int(active[i]))
