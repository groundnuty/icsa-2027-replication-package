import numpy as np, datetime as dt, json, os

z = np.load('mhw_cache.npz', allow_pickle=False)
tgt_data = z['tgt_data'].astype(np.float64)   # (92, 60, 60)
tgt_t = z['tgt_t']
c = np.load('clim_thr.npz')
thr_s = c['thr']; clm_s = c['clm']

def doy366(d):
    cum_norm = [0,31,59,90,120,151,181,212,243,273,304,334]
    if d.month == 2 and d.day == 29:
        return 60
    v = cum_norm[d.month-1] + d.day
    if d.month >= 3:
        v += 1
    return v

tgt_days = [dt.date(2004,6,1)+dt.timedelta(days=int(k)) for k in range(tgt_data.shape[0])]
tgt_doy = np.array([doy366(d) for d in tgt_days])
print("target doys:", tgt_doy[0], "...", tgt_doy[-1])

# sea cells: finite on every target day
sea = np.isfinite(tgt_data).all(axis=0)
print("sea cells:", int(sea.sum()), "of", sea.size)

hot = tgt_data >= thr_s[tgt_doy-1]        # NaN -> False
hot[:, ~sea] = False
print("hot day-cell fraction (sea):", hot[:, sea].mean().round(4))

def runs_of_true(h):
    idx = np.flatnonzero(np.diff(np.concatenate(([0], h.view(np.int8), [0]))))
    return list(zip(idx[0::2], idx[1::2]-1))   # inclusive (s,e)

def cell_mhw_intervals(h):
    """runs>=5 hot, join gaps of 1-2 non-hot days; return merged inclusive intervals"""
    ivs = [(s,e) for s,e in runs_of_true(h) if e-s+1 >= 5]
    if not ivs: return []
    merged = [list(ivs[0])]
    for s,e in ivs[1:]:
        if s - merged[-1][1] - 1 <= 2:
            merged[-1][1] = e
        else:
            merged.append([s,e])
    return [tuple(m) for m in merged]

NT, NY, NX = hot.shape
mhw = np.zeros((NT, NY, NX), dtype=np.uint8)
n_cells_with = 0; all_iv = []
for i in range(NY):
    for j in range(NX):
        if not sea[i,j]: continue
        ivs = cell_mhw_intervals(hot[:,i,j])
        if ivs:
            n_cells_with += 1
            all_iv += ivs
            for s,e in ivs:
                mhw[s:e+1, i, j] = 1
print("cells with >=1 per-cell MHW:", n_cells_with, "| total per-cell MHW intervals (post-join):", len(all_iv))
lens = [e-s+1 for s,e in all_iv]
if lens: print("per-cell MHW lengths: min", min(lens), "max", max(lens), "mean", round(float(np.mean(lens)),2))

active = mhw.reshape(NT, -1).any(axis=1)
ev_runs = runs_of_true(active)
events = [{"onset": str(tgt_days[s]), "end": str(tgt_days[e])} for s,e in ev_runs]
print("active days:", int(active.sum()), "of", NT)
print("regional events:")
for ev in events: print("  ", ev)

os.makedirs('output', exist_ok=True)
np.save('mhw_mask_arr.npy', mhw)
with open('events_tmp.json','w') as f:
    json.dump(events, f)
print("masked cell-days:", int(mhw.sum()))
