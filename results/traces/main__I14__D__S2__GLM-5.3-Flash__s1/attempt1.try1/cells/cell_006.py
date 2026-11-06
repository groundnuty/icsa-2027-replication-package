import numpy as np, xarray as xr, warnings
from datetime import date, timedelta
warnings.filterwarnings('ignore')

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
d64 = ds['time'].values.astype('datetime64[D]')
def ix(y,m,d):
    return int((np.datetime64(f'{y:04d}-{m:02d}-{d:02d}') - d64[0]).astype(np.int64))
lo, hi = ix(1991,12,26), ix(2003,1,6)
b = np.load('/work/blocks.npz')['b'] if False else None
# reload blocks from npz (already saved)
z = np.load('/work/blocks.npz', allow_pickle=True)
b = z['b']; tgt = z['tgt']
flat = b.reshape(b.shape[0], -1)
bdates = [d.item() if hasattr(d,'item') else d for d in d64[lo:hi+1].astype('O')]
bdates = [x.item() if isinstance(x, np.generic) else x for x in bdates]
print('bdates type', type(bdates[0]), bdates[0], bdates[-1], len(bdates))
off = [0,31,60,91,121,152,182,213,244,274,305,335]
def fdoy(d):
    if d.month==2 and d.day==29: return 60
    return off[d.month-1]+d.day
blo, bhi = date(1992,1,1), date(2002,12,31)
bdates_core = [d for d in bdates if blo <= d <= bhi]
print('core baseline dates:', len(bdates_core))
pos = {d:i for i,d in enumerate(bdates)}

def pool_dates(d):
    centers = [c for c in bdates_core if fdoy(c)==d]
    mem = set()
    for c in centers:
        for k in range(-5,6):
            m = c + timedelta(days=k)
            if date(1991,12,27) <= m <= date(2003,1,5):
                mem.add(m)
    return sorted(mem), centers

rng = np.random.default_rng(7)
cells = rng.choice(3600, 8, replace=False)
def pools_for(doys):
    out = {}
    for d in doys:
        if d == 60: continue
        pd, centers = pool_dates(d)
        idx = np.array(sorted(pos[m] for m in pd))
        out[d] = idx
        if d==1: p1 = pd
        if d==366: p366 = pd
    return out, p1, p366
test_doys = [1,2,55,58,59,60,61,152,153,200,243,244,365,366]
pools, p1, p366 = pools_for(test_doys)
print('pool lens:', {d: len(pools[d]) for d in pools})
print('doy1 pool: n=%d first=%s last=%s has1991=%s has2003=%s' % (len(p1), p1[0], p1[-1],
      any(x.year==1991 for x in p1), any(x.year==2003 for x in p1)))
print('doy366 pool: n=%d first=%s last=%s has1991=%s has2003=%s Feb29members=%d' % (len(p366), p366[0], p366[-1],
      any(x.year==1991 for x in p366), any(x.year==2003 for x in p366),
      sum(1 for x in p366 if x.month==2 and x.day==29)))

def hazen_q(col, p=0.9):
    v = col[np.isfinite(col)]
    n = v.size
    if n == 0: return np.nan
    v = np.sort(v)
    h = p*n + 0.5
    lo_i = int(np.floor(h)); hi_i = int(np.ceil(h))
    lo_i = max(1, min(lo_i, n)); hi_i = max(1, min(hi_i, n))
    if lo_i == hi_i: return float(v[lo_i-1])
    return float(v[lo_i-1] + (h-lo_i)*(v[hi_i-1]-v[lo_i-1]))

raw_thr = np.full((366, len(cells)), np.nan); raw_clim = np.full_like(raw_thr, np.nan)
vec_thr = np.full_like(raw_thr, np.nan); vec_clim = np.full_like(raw_thr, np.nan)
for d in range(1,367):
    if d == 60: continue
    pd_, _ = pool_dates(d)
    idx = np.array(sorted(pos[m] for m in pd_))
    blk = flat[idx][:, cells]
    for k in range(len(cells)):
        raw_thr[d-1,k] = hazen_q(blk[:,k])
        v = blk[np.isfinite(blk[:,k]), k]
        raw_clim[d-1,k] = v.mean() if v.size else np.nan
    vec_thr[d-1] = np.nanquantile(blk, 0.9, axis=0, method='hazen')
    vec_clim[d-1] = np.nanmean(blk, axis=0)
for arr in (raw_thr, raw_clim, vec_thr, vec_clim):
    arr[59] = 0.5*(arr[58]+arr[60])
w = (np.arange(366)[:,None] + np.arange(-15,16)[None,:]) % 366
s_thr = raw_thr[w].mean(axis=1); s_clim = raw_clim[w].mean(axis=1)
v_thr = vec_thr[w].mean(axis=1); v_clim = vec_clim[w].mean(axis=1)
print('manual-vs-vectorised raw thr max|diff|:', np.nanmax(np.abs(raw_thr-vec_thr)))
print('manual-vs-vectorised raw clim max|diff|:', np.nanmax(np.abs(raw_clim-vec_clim)))
print('smoothed: manual-vs-vectorised thr max|diff|:', np.nanmax(np.abs(s_thr-v_thr)))
print('smoothed: manual-vs-vectorised clim max|diff|:', np.nanmax(np.abs(s_clim-v_clim)))

# save the region SST blocks locally for a fast third pass
np.savez_compressed('/work/reg_blocks.npz', b=b, tgt=tgt)
print('region blocks re-saved')
