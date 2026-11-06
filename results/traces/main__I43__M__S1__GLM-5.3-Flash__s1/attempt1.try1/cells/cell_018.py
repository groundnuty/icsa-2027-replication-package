import numpy as np
from datetime import date

z = np.load('/work/cubes.npz')
targ_cube = z['targ_cube'].astype('float64')          # (92, 60, 60)
targ_ds = [date.fromisoformat(str(s)) for s in z['targ_dates']]
CUM = np.array([0,31,60,91,121,152,182,213,244,274,305,335,366])
targ_doy = np.array([CUM[d.month-1] + d.day for d in targ_ds])
sea_flat = np.load('/work/sea_flat.npy')

clim = np.load('/work/clim.npz')
thr_s = clim['thr_s']                                  # (366, 3308)

T = targ_cube.reshape(len(targ_ds), -1)                # (92, 3600)
targ_sea = T[:, sea_flat]                              # (92, 3308)
hot = targ_sea >= thr_s[targ_doy - 1, :]               # (92, 3308) bool
print('hot days total:', int(hot.sum()), 'of', hot.size, '(%.1f%%)' % (100*hot.mean()))

nsea = hot.shape[1]
mhw_sea = np.zeros_like(hot, dtype=bool)
n_runs_raw = 0; n_runs_final = 0; run_len_list = []
for c in range(nsea):
    h = hot[:, c]
    # run-length encode
    idx = np.flatnonzero(np.diff(np.r_[0, h.view(np.int8), 0]))
    # starts at idx[0::2], ends at idx[1::2] (exclusive)
    starts = idx[0::2]; ends = idx[1::2]              # day indices [start, end)
    runs = list(zip(starts.tolist(), ends.tolist()))
    n_runs_raw += len(runs)
    # keep runs >= 5
    runs = [(s, e) for (s, e) in runs if e - s >= 5]
    if not runs: continue
    # merge runs separated by 1 or 2 non-hot days
    merged = [list(runs[0])]
    for s, e in runs[1:]:
        if s - merged[-1][1] in (1, 2):
            merged[-1][1] = e
        else:
            merged.append([s, e])
    n_runs_final += len(merged)
    for s, e in merged:
        run_len_list.append(e - s)
        mhw_sea[s:e, c] = True

run_len_arr = np.array(run_len_list)
print('per-cell runs raw:', n_runs_raw, '| runs >=5d:', len(run_len_arr), '| after joining:', n_runs_final)
print('per-cell MHW length: min %d max %d mean %.1f | n cells with >=1 MHW: %d' %
      (run_len_arr.min(), run_len_arr.max(), run_len_arr.mean(), int((mhw_sea.any(axis=0)).sum())))
print('per-cell MHW days total:', int(mhw_sea.sum()))

active = mhw_sea.any(axis=1)                           # (92,) regional active days
print('active days:', int(active.sum()), 'of 92')
# regional events: maximal runs of active
act = active.astype(np.int8)
eidx = np.flatnonzero(np.diff(np.r_[0, act, 0]))
evs = [(int(eidx[i]), int(eidx[i+1])) for i in range(0, len(eidx), 2)]
print('regional events:', len(evs))
for s, e in evs:
    print('  %s .. %s  (%d days)' % (targ_ds[s].isoformat(), targ_ds[e-1].isoformat(), e-s))
np.savez_compressed('/work/mhw_sea.npz', mhw_sea=mhw_sea, active=active)
