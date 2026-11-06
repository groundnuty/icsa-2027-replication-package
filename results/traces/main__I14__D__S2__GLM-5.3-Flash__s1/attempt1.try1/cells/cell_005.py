import numpy as np, xarray as xr, warnings
from datetime import date, timedelta
warnings.filterwarnings('ignore')

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
d64 = ds['time'].values.astype('datetime64[D]')
t0 = d64[0]
def ix(y,m,d):
    k = int((np.datetime64(f'{y:04d}-{m:02d}-{d:02d}') - t0).astype(np.int64))
    return k
lo, hi = ix(1991,12,26), ix(2003,1,6)
glo, ghi = ix(2015,6,1), ix(2015,8,31)
sl = dict(latitude=slice(132,192), longitude=slice(436,496))
b = ds['analysed_sst'].isel(time=slice(lo,hi+1), **sl).values.astype('float64')
tgt = ds['analysed_sst'].isel(time=slice(glo,ghi+1), **sl).values.astype('float64')
np.savez_compressed('/work/blocks.npz', b=b, tgt=tgt,
                    bdates=d64[lo:hi+1].astype('O'), gdates=d64[glo:ghi+1].astype('O'))
print('saved blocks', b.shape, tgt.shape)

# ---------- independent date-based pool construction ----------
bdates = [dd.item() for dd in d64[lo:hi+1].astype('O')]  # datetime.date list, 1991-12-26..2003-01-06
off = [0,31,60,91,121,152,182,213,244,274,305,335]
def fdoy(d):  # fixed 366-cal doy
    if d.month==2 and d.day==29: return 60
    return off[d.month-1]+d.day
blo, bhi = date(1992,1,1), date(2002,12,31)
bdates_core = [d for d in bdates if blo <= d <= bhi]
print('core baseline dates:', len(bdates_core))

def pool_dates(d):
    centers = [c for c in bdates_core if fdoy(c)==d]
    assert centers, d
    mem = set()
    for c in centers:
        for k in range(-5,6):
            m = c + timedelta(days=k)
            if date(1991,12,27) <= m <= date(2003,1,5):
                mem.add(m)
    return sorted(mem), centers

# index of a date in the loaded block (block covers 1991-12-26..2003-01-06 contiguous)
pos = {d:i for i,d in enumerate(bdates)}

thr_u = np.load('/work/thr_s.npy'); clim_u = np.load('/work/clim_s.npy')  # NOTE these are SMOOTHED; recompute raw below
flat = b.reshape(b.shape[0], -1)
rng = np.random.default_rng(7)
cells = rng.choice(3600, 8, replace=False)
test_doys = [1,2,55,58,59,60,61,152,153,200,243,244,365,366]
maxpool = 0
for d in test_doys:
    if d == 60: continue
    pd, centers = pool_dates(d)
    idx = np.array(sorted(pos[m] for m in pd))
    maxpool = max(maxpool, len(idx))
    blk = flat[idx][:, cells]
    q = np.nanquantile(blk, 0.9, axis=0, method='hazen')
    mn = np.nanmean(blk, axis=0)
    if d == 1:
        pool1_idx = idx; pool1_dates = pd
    if d == 366:
        pool366_idx = idx; pool366_dates = pd
print('max pool len over test doys:', maxpool)
print('doy1 pool: n=', len(pool1_dates), 'first:', pool1_dates[0], 'last:', pool1_dates[-1],
      'has1991?', any(x.year==1991 for x in pool1_dates), 'has2003?', any(x.year==2003 for x in pool1_dates))
print('doy366 pool: n=', len(pool366_dates), 'first:', pool366_dates[0], 'last:', pool366_dates[-1],
      'has1991?', any(x.year==1991 for x in pool366_dates), 'has2003?', any(x.year==2003 for x in pool366_dates),
      'Feb29 members:', sum(1 for x in pool366_dates if x.month==2 and x.day==29))

# manual Hazen (type 5): h = p*n + 0.5 on sorted (nan-removed) column, linear interp
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

# rebuild raw (unsmoothed) threshold/clim for the 8 sample cells across all doys, date-based
raw_thr = np.full((366, len(cells)), np.nan); raw_clim = np.full_like(raw_thr, np.nan)
for d in range(1,367):
    if d == 60: continue
    pd_, _ = pool_dates(d)
    idx = np.array(sorted(pos[m] for m in pd_))
    blk = flat[idx][:, cells]
    for k in range(len(cells)):
        raw_thr[d-1,k] = hazen_q(blk[:,k])
        v = blk[np.isfinite(blk[:,k]), k]
        raw_clim[d-1,k] = v.mean() if v.size else np.nan
# compare vs the vectorised nanquantile path for these cells
flat_cells = flat[:, cells]
vec_thr = np.full((366, len(cells)), np.nan); vec_clim = np.full_like(vec_thr, np.nan)
for d in range(1,367):
    if d == 60: continue
    pd_, _ = pool_dates(d)
    idx = np.array(sorted(pos[m] for m in pd_))
    blk = flat[idx][:, cells]
    vec_thr[d-1] = np.nanquantile(blk, 0.9, axis=0, method='hazen')
    vec_clim[d-1] = np.nanmean(blk, axis=0)
raw_thr[59] = 0.5*(raw_thr[58]+raw_thr[60]); raw_clim[59] = 0.5*(raw_clim[58]+raw_clim[60])
vec_thr[59] = 0.5*(vec_thr[58]+vec_thr[60]); vec_clim[59] = 0.5*(vec_clim[58]+vec_clim[60])
w = (np.arange(366)[:,None] + np.arange(-15,16)[None,:]) % 366
s_thr = raw_thr[w].mean(axis=1); s_clim = raw_clim[w].mean(axis=1)
v_thr = vec_thr[w].mean(axis=1); v_clim = vec_clim[w].mean(axis=1)
print('raw thr manual-vs-vectorised max|diff|:', np.nanmax(np.abs(raw_thr-vec_thr)))
print('smoothed thr sample-cells vs pipeline max|diff|:', np.nanmax(np.abs(s_thr - thr_u[:, cells])))
print('smoothed clim sample-cells vs pipeline max|diff|:', np.nanmax(np.abs(s_clim - clim_u[:, cells])))
np.savez('/work/verify_cells.npz', cells=cells, s_thr=s_thr, s_clim=s_clim)
print('verify cells:', cells)
