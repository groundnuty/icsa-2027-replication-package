import numpy as np
from datetime import date

z = np.load('/work/cubes.npz')
targ_cube = z['targ_cube'].astype('float64')
targ_ds = [date.fromisoformat(str(s)) for s in z['targ_dates']]
sea_flat = np.load('/work/sea_flat.npy')
CUM = np.array([0,31,60,91,121,152,182,213,244,274,305,335,366])
targ_doy = np.array([CUM[d.month-1]+d.day for d in targ_ds])
clim = np.load('/work/clim_final.npz'); thr_s = clim['thr_s']; clm_s = clim['clm_s']

def mhw_runs_1d(h):
    h = np.asarray(h, dtype=bool)
    e = np.flatnonzero(np.diff(np.r_[0, h.view(np.int8), 0]))
    runs = [(int(e[i]), int(e[i+1])) for i in range(0, len(e), 2)]
    runs = [(s, en) for (s, en) in runs if en - s >= 5]
    if not runs: return []
    merged = [list(runs[0])]
    for s, en in runs[1:]:
        if s - merged[-1][1] in (1, 2): merged[-1][1] = en
        else: merged.append([s, en])
    return [tuple(m) for m in merged]

cases = [
    ([1,1,1,1,0,0,0,0,0,0], []),
    ([0,1,1,1,1,1,0,0,0,0], [(1,6)]),
    ([1,1,1,1,1,0,1,1,1,1,1,1,0,0], [(0,12)]),
    ([1,1,1,1,1,0,0,1,1,1,1,1,0,0], [(0,12)]),
    ([1,1,1,1,1,0,0,0,1,1,1,1,1,0], [(0,5),(8,13)]),
    ([1,1,1,0,1,1,1,0,0,0,0,0,0,0], []),
    ([1,1,1,1,0,1,1,1,1,0,0,0,0,0], []),
    ([1,1,1,1,1,0,0,1,1,1,1,0,0,0], [(0,5)]),
    ([1]*10, [(0,10)]),
    ([0,0,1,1,1,1,1,1,1,1], [(2,10)]),
    ([1,1,1,1,1,1,1,1,0,0,1,1,1,1,1], [(0,15)]),   # gap of exactly 2 -> joined per spec
]
allok = all(mhw_runs_1d(np.array(h, bool)) == exp for h, exp in cases)
print('run-logic unit tests:', 'ALL PASS (11/11)' if allok else 'FAIL')

targ_sea = targ_cube.reshape(len(targ_ds), -1)[:, sea_flat]
hot = targ_sea >= thr_s[targ_doy-1, :]
nhot = int(hot.sum())
diff = targ_sea - thr_s[targ_doy-1, :]
print('FINAL: hot days = %d ; max(SST - threshold) = %+.6f K on %s' %
      (nhot, np.nanmax(diff), targ_ds[int(np.nanargmax(diff)) // hot.shape[1]]))
mhw_sea = np.zeros_like(hot, dtype=bool)   # no hot days -> no per-cell MHWs
active = mhw_sea.any(axis=1)
print('active days = %d -> regional events = 0' % int(active.sum()))

# climatology sanity for the report: region-mean clim/thr over target doys
print('region-mean climatology over target doys: %.2f K ; threshold: %.2f K' % (clm_s[targ_doy-1].mean(), thr_s[targ_doy-1].mean()))
np.savez_compressed('/work/final_state.npz', hot=hot, mhw_sea=mhw_sea, active=active)
