import numpy as np, datetime as dt, json

z = np.load('/tmp/region_cube.npz', allow_pickle=True)
dates_str = z['dates']; cube32 = z['cube']
BLK = 4028
tc = np.load('/tmp/thr_clim.npz')
thr = tc['thr']; clim = tc['clim']; sea = tc['sea']  # thr/clim (366, 3292) float64, sea (60,60)
C = thr.shape[1]

# day-of-year for target days (month/day mapping)
CUM = [0,31,59,90,120,151,181,212,243,273,304,334]
def doy_map(d):
    return CUM[d.month-1] + d.day + (1 if d.month > 2 else 0)
tgt_dates = [dt.datetime.strptime(str(s), '%Y%m%d').date() for s in dates_str[BLK:]]
tgt_doy = np.array([doy_map(d) for d in tgt_dates]) - 1   # 0-based
print("target dates:", tgt_dates[0], "..", tgt_dates[-1], "n=", len(tgt_dates))

sst = cube32[BLK:, :, :60].astype(np.float64).reshape(92, -1)[:, sea.reshape(-1)]  # (92, 3292)
thr_t = thr[tgt_doy]     # (92, 3292)
clim_t = clim[tgt_doy]

# hot days
hot = sst >= thr_t
print("hot days total:", hot.sum(), "per-day active min/max:", hot.sum(axis=1).min(), hot.sum(axis=1).max())

# runs >= 5 via prev/next false index
T = 92
tcol = np.arange(T)[:, None]
prev_false = np.maximum.accumulate(np.where(~hot, tcol, -1), axis=0)
nxt_false = np.minimum.accumulate(np.where(~hot, tcol, T)[::-1], axis=0)[::-1]
runlen = np.where(hot, nxt_false - prev_false - 1, 0)
m5 = hot & (runlen >= 5)
print("days in >=5 runs:", m5.sum())

# fill bounded False-gaps of length 1-2
prev_true = np.maximum.accumulate(np.where(m5, tcol, -1), axis=0)
nxt_true = np.minimum.accumulate(np.where(m5, tcol, T)[::-1], axis=0)[::-1]
gaplen = nxt_true - prev_true - 1
fill = (~m5) & (prev_true >= 0) & (nxt_true <= T-1) & (gaplen <= 2)
mhw = m5 | fill
print("gap days filled:", fill.sum(), "total MHW cell-days:", mhw.sum())

# per-cell MHW event counts (runs in final mask)
def count_runs(m):  # m: (T,C) bool
    mp = np.vstack([np.zeros((1, m.shape[1]), bool), m, np.zeros((1, m.shape[1]), bool)])
    d = np.diff(mp.astype(np.int8), axis=0)
    return (d == 1).sum()
print("per-cell MHW events:", count_runs(mhw))
print("cells with >=1 MHW:", mhw.any(axis=0).sum())

# regional events
active = mhw.any(axis=1)
print("active days:", active.sum(), "of", T)
ev = []
in_ev = False
for i, a in enumerate(active):
    if a and not in_ev: start = i; in_ev = True
    if not a and in_ev: ev.append((start, i-1)); in_ev = False
if in_ev: ev.append((start, T-1))
print("regional events:", [(tgt_dates[s].isoformat(), tgt_dates[e].isoformat(), e-s+1) for s, e in ev])
np.savez('/tmp/mhw_result.npz', mhw=mhw, active=active, hot=hot, tgt_doy=tgt_doy)
