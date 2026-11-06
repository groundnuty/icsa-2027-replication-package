import numpy as np
from datetime import date

z = np.load('/work/cubes.npz')
base_cube = z['base_cube']; targ_cube = z['targ_cube'].astype('float64')
base_ds = [date.fromisoformat(str(s)) for s in z['base_dates']]
targ_ds = [date.fromisoformat(str(s)) for s in z['targ_dates']]
sea_flat = np.load('/work/sea_flat.npy')
is_seed = np.load('/work/ord_is_seed.npy')
CUM = np.array([0,31,60,91,121,152,182,213,244,274,305,335,366])
def md_doy(d): return int(CUM[d.month-1]+d.day)

ords = np.array([d.toordinal() for d in base_ds])
base_doy = np.array([md_doy(d) for d in base_ds])
base_sea = base_cube.reshape(len(base_ds), -1)[:, sea_flat].astype('float64')

pools = {}
for dd in range(1, 367):
    if dd == 60: continue
    seed_ord = ords[is_seed & (base_doy == dd)]
    pools[dd] = np.where((np.abs(ords[:, None] - seed_ord[None, :]) <= 5).any(axis=1))[0]
assert all(len(p) == 121 for p in pools.values())

nsea = base_sea.shape[1]
thr = np.full((366, nsea), np.nan); clm = np.full((366, nsea), np.nan)
for dd in range(1, 367):
    if dd == 60: continue
    vals = base_sea[pools[dd]]
    thr[dd-1] = np.nanquantile(vals, 0.9, axis=0, method='hazen')
    clm[dd-1] = np.nanmean(vals, axis=0)
thr[59] = 0.5*(thr[58]+thr[60]); clm[59] = 0.5*(clm[58]+clm[60])
idx = (np.arange(366)[:, None] + np.arange(-15, 16)[None, :]) % 366
thr_s = thr[idx].mean(axis=1); clm_s = clm[idx].mean(axis=1)
assert np.isfinite(thr_s).all() and np.isfinite(clm_s).all()
np.savez_compressed('/work/clim_final.npz', thr_s=thr_s, clm_s=clm_s)
print('climatology recomputed with corrected pools; saved clim_final.npz')

# ---- MHW detection on target period ----
targ_sea = targ_cube.reshape(len(targ_ds), -1)[:, sea_flat]
targ_doy = np.array([md_doy(d) for d in targ_ds])
hot = targ_sea >= thr_s[targ_doy-1, :]
print('hot days:', int(hot.sum()))
diff = targ_sea - thr_s[targ_doy-1, :]
print('max(SST-thr) = %+.6f K' % np.nanmax(diff))

def mhw_runs_1d(h):
    """Return list of (start, end_exclusive) per-cell MHW intervals per spec step 3."""
    h = np.asarray(h, dtype=bool)
    e = np.flatnonzero(np.diff(np.r_[0, h.view(np.int8), 0]))
    runs = [(int(e[i]), int(e[i+1])) for i in range(0, len(e), 2)]
    runs = [(s, en) for (s, en) in runs if en - s >= 5]          # >= 5 consecutive hot days
    if not runs: return []
    merged = [list(runs[0])]
    for s, en in runs[1:]:
        if s - merged[-1][1] in (1, 2): merged[-1][1] = en      # join gaps of 1-2 days
        else: merged.append([s, en])
    return [tuple(m) for m in merged]

# ---- unit tests of the run logic ----
cases = [
    ([1,1,1,1,0,0,0,0,0,0], []),                                # run of 4 -> none
    ([0,1,1,1,1,1,0,0,0,0], [(1,6)]),                           # run of 5
    ([1,1,1,1,1,0,1,1,1,1,1,1,0,0], [(0,12)]),                  # 5 + gap1 + 6 -> joined
    ([1,1,1,1,1,0,0,1,1,1,1,1,0,0], [(0,12)]),                  # 5 + gap2 + 5 -> joined
    ([1,1,1,1,1,0,0,0,1,1,1,1,1,0], [(0,5),(8,13)]),            # gap3 -> two MHWs
    ([1,1,1,0,1,1,1,0,0,0,0,0,0,0], []),                        # 3+1+3: no MHW, nothing to join
    ([1,1,1,1,0,1,1,1,1,0,0,0,0,0], []),                        # 4+1+4: no MHWs
    ([1,1,1,1,1,0,0,1,1,1,1,0,0,0], [(0,5)]),                   # 5 + gap2 + 4(short) -> only first
    ([1]*10, [(0,10)]),                                         # run touching start
    ([0,0,1,1,1,1,1,1,1,1], [(2,10)]),                          # run touching end
    ([1,1,1,1,1,1,1,1,0,0,1,1,1,1,1], [(0,8),(10,15)]),         # gap exactly 2 -> join
]
allok = True
for i, (h, exp) in enumerate(cases):
    got = mhw_runs_1d(np.array(h, dtype=bool))
    if got != exp:
        allok = False; print('FAIL case', i, 'got', got, 'expected', exp)
print('run-logic unit tests:', 'ALL PASS' if allok else 'FAILURES')
