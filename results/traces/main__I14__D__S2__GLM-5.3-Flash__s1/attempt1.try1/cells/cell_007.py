import numpy as np, warnings
from datetime import date, timedelta
warnings.filterwarnings('ignore')

z = np.load('/work/blocks.npz', allow_pickle=True)
b, tgt = z['b'], z['tgt']
bdates = [x.item() if isinstance(x, np.generic) else x for x in z['bdates']]
gdates = [x.item() if isinstance(x, np.generic) else x for x in z['gdates']]
flat = b.reshape(b.shape[0], -1)

thr_u = np.load('/work/thr_s.npy'); clim_u = np.load('/work/clim_s.npy')
v = np.load('/work/verify_cells.npz') if False else None
off = [0,31,60,91,121,152,182,213,244,274,305,335]
def fdoy(d):
    if d.month==2 and d.day==29: return 60
    return off[d.month-1]+d.day
blo, bhi = date(1992,1,1), date(2002,12,31)
core = [d for d in bdates if blo <= d <= bhi]
pos = {d:i for i,d in enumerate(bdates)}
lo_lim, hi_lim = date(1991,12,27), date(2003,1,5)
def pool_idx(d):
    mem = set()
    for c in core:
        if fdoy(c)==d:
            for k in range(-5,6):
                m = c+timedelta(days=k)
                if lo_lim <= m <= hi_lim: mem.add(m)
    return np.array(sorted(pos[m] for m in mem))
rng = np.random.default_rng(7)
cells = np.sort(rng.choice(3600, 8, replace=False))
raw_thr = np.full((366,len(cells)), np.nan); raw_clim = np.full_like(raw_thr, np.nan)
for d in range(1,367):
    if d==60: continue
    blk = flat[pool_idx(d)][:, cells]
    for k in range(len(cells)):
        col = blk[:,k]; vv = col[np.isfinite(col)]
        n = vv.size
        if n:
            s = np.sort(vv); h = 0.9*n+0.5
            lo_i, hi_i = int(np.floor(h)), int(np.ceil(h))
            lo_i = max(1,min(lo_i,n)); hi_i = max(1,min(hi_i,n))
            raw_thr[d-1,k] = s[lo_i-1] if lo_i==hi_i else s[lo_i-1]+(h-lo_i)*(s[hi_i-1]-s[lo_i-1])
            raw_clim[d-1,k] = vv.mean()
for a in (raw_thr, raw_clim): a[59] = 0.5*(a[58]+a[60])
w = (np.arange(366)[:,None] + np.arange(-15,16)[None,:]) % 366
s_thr = raw_thr[w].mean(axis=1); s_clim = raw_clim[w].mean(axis=1)
print('date-based smoothed thr vs pipeline thr_s, max|diff|:', np.nanmax(np.abs(s_thr - thr_u[:, cells])))
print('date-based smoothed clim vs pipeline clim_s, max|diff|:', np.nanmax(np.abs(s_clim - clim_u[:, cells])))

# ---------------- independent target-phase re-run (different algorithm) ----------------
tflat = tgt.reshape(tgt.shape[0], -1)
t_doy = np.array([fdoy(d) for d in gdates])
sea = np.isfinite(tflat).all(axis=0)
hot = np.zeros_like(tflat, dtype=bool)
hot[:, sea] = tflat[:, sea] >= thr_u[t_doy-1][:, sea]
hot[:, ~sea] = False
T, C = hot.shape

# independent run extraction: iterate cells with an explicit state machine, then join gaps
mhw_indep = np.zeros((T, C), np.uint8)
nruns0 = njoined = 0
for c in range(C):
    hs = hot[:, c]
    if not hs.any(): continue
    runs = []
    i = 0
    while i < T:
        if hs[i]:
            j = i
            while j+1 < T and hs[j+1]: j += 1
            runs.append([i, j])  # inclusive
            i = j+1
        else:
            i += 1
    long_runs = [r for r in runs if r[1]-r[0]+1 >= 5]
    nruns0 += len(long_runs)
    # join runs separated by 1 or 2 non-hot days
    out = []
    for r in long_runs:
        if out and r[0]-out[-1][1] <= 3:  # gap days = r[0]-prev_end-1 <= 2  <=>  r[0]-prev_end <= 3
            out[-1][1] = r[1]; njoined += 1
        else:
            out.append(r)
    for s_, e_ in out:
        mhw_indep[s_:e_+1, c] = 1
print('indep: raw long runs', nruns0, '| joins performed', njoined, '| final per-cell MHWs', nruns0-njoined)
mask_prev = np.load('/work/diag.npz')['mask'].reshape(T, C)
print('mask identical to pipeline:', bool((mhw_indep == mask_prev).all()))
print('total MHW cells-days:', int(mhw_indep.sum()))
active = mhw_indep.any(axis=1)
runsA = []
i = 0
while i < T:
    if active[i]:
        j = i
        while j+1 < T and active[j+1]: j += 1
        runsA.append((i, j)); i = j+1
    else: i += 1
print('indep events:', [(str(gdates[a]), str(gdates[bb])) for a, bb in runsA])
print('per-day hot-cell counts:', hot.sum(axis=1).tolist())
print('per-day in-MHW-cell counts:', mhw_indep.sum(axis=1).tolist())
np.savez('/work/indep_mask.npz', mhw=mhw_indep)
