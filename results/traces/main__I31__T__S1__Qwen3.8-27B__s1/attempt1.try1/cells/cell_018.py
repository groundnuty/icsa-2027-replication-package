
import numpy as np, time, datetime

thr = np.load('work/thr_raw.npy')    # (366, 3600) float64
clim = np.load('work/clim_raw.npy')
S_tgt = np.load('work/S_tgt.npy')    # (92, 60, 60) float32
N = 3600

def circ_mmean31(a):
    # a: (366, M) float64 -> circular centred 31-day moving mean
    ext = np.concatenate([a[-15:], a, a[:15]], axis=0)   # (396, M)
    c = np.empty((ext.shape[0]+1, ext.shape[1]), dtype=np.float64)
    c[0] = 0.0
    np.cumsum(ext, axis=0, out=c[1:])
    return (c[31:] - c[:-31]) / 31.0

# verify against naive loop on one cell
a = thr[:, 0]
sm = circ_mmean31(thr)
for d in [0, 14, 15, 44, 59, 60, 61, 350, 360, 365]:
    ref = np.mean(np.array([a[(d+k) % 366] for k in range(-15, 16)]))
    assert abs(sm[d, 0] - ref) < 1e-9 * max(1, abs(ref)), (d, sm[d,0], ref)
print("smoothing verified vs naive")

thr_s = circ_mmean31(thr)
clim_s = circ_mmean31(clim)
np.save('work/thr_smooth.npy', thr_s)
np.save('work/clim_smooth.npy', clim_s)
print("smoothing done; NaN cells thr_s:", int(np.isnan(thr_s).any(axis=0).sum()))

# target dates and day-of-year
mday = [31,29,31,30,31,30,31,31,30,31,30,31]
cdf_prev = np.concatenate([[0], np.cumsum(mday)[:-1]])
t0 = datetime.date(2017,6,1)
tgt_dates = [t0 + datetime.timedelta(days=i) for i in range(92)]
doy_t = cdf_prev[np.array([d.month for d in tgt_dates])-1] + np.array([d.day for d in tgt_dates])
print("target doy range:", doy_t.min(), doy_t.max(), "any 60?:", (doy_t==60).any())
print("first/last:", tgt_dates[0], tgt_dates[-1])

sea = np.isfinite(S_tgt).all(axis=0).reshape(-1)
print("sea cells:", int(sea.sum()))
S64 = S_tgt.astype(np.float64).reshape(92, N)
H = (S64 >= thr_s[doy_t][:, None, :]) & sea[None, :]
# non-sea cells must be False even if NaN comparison somehow True (it isn't)
print("hot days total:", int(H.sum()), " cells with any hot day:", int(H.any(axis=0).sum()))
print("hot fraction on doy-182 (Jun30):", float(H[29][sea].mean()) if H.shape[0]>29 else 'n/a')
np.save('work/H.npy', H)
np.save('work/sea.npy', sea)
np.save('work/doy_t.npy', doy_t)

# ---- per-cell MHW: runs of >=5 hot days, merge runs separated by <=2 non-hot days
T = 92
d = np.diff(np.concatenate([np.zeros((1, N), bool), H, np.zeros((1, N), bool)], axis=0), axis=0)
# d shape (93, N): d[t+1] = H[t]-H[t-1]
starts = np.argwhere(d == 1)   # (t_idx, cell) with start day = t_idx-1 ... verify
# d index i corresponds to transition after day i-1; d[i]==1 means H[i-1] became True -> start day i-1? 
# Actually d[i] = H[i-1] - H[i-2] for i=1..91 (with H[-1]=H[92]=False sentinels)
# d[i]==1 => H[i-1]=1 and H[i-2]=0 => run starts at day i-1
# d[i]==-1 => run ends at day i-2
si = np.where(d == 1)
ei = np.where(d == -1)
assert si[0].min() >= 1 and ei[0].max() <= T
start_day = si[0] - 1          # 0-based day
end_day = ei[0] - 2
cell_ids = si[1]
# align by order: runs in each cell are in day order; si and ei have same per-cell ordering
# build per-cell list
runs_by_cell = {}
for c, s, e in zip(cell_ids, start_day, end_day):
    runs_by_cell.setdefault(c, []).append((int(s), int(e)))
# check counts match
assert len(np.unique(cell_ids)) == len(runs_by_cell)

mask = np.zeros((T, N), dtype=np.uint8)
n_mhws = 0
for c, runs in runs_by_cell.items():
    segs = []
    for s, e in runs:
        L = e - s + 1
        if L < 5:
            continue
        if segs and s - segs[-1][1] - 1 <= 2:
            segs[-1] = (segs[-1][0], e)
        else:
            segs.append([s, e])
    n_mhws += len(segs)
    for s, e in segs:
        mask[s:e+1, c] = 1
print("per-cell MHW segments:", n_mhws, " mask days:", int(mask.sum()))
np.save('work/mask.npy', mask)

active = mask.any(axis=1)
ev_d = np.diff(np.concatenate([[0], active.astype(int), [0]]))
onsets = np.where(ev_d == 1)[0]
ends = np.where(ev_d == -1)[0]
print("onset days (0-based):", onsets.tolist())
print("end days (0-based):", ends.tolist())
events = [(str(tgt_dates[o]), str(tgt_dates[e-1])) for o, e in zip(onsets, ends)]
print("events:", events)
# active day counts
print("active days total:", int(active.sum()))
