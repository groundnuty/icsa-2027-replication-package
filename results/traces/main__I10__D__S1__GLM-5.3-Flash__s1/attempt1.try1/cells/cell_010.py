import numpy as np, datetime as dt, json, warnings, time
warnings.filterwarnings('ignore')

CUM = [0,31,60,91,121,152,182,213,244,274,305,335]
def mdoy(y,m,d): return CUM[m-1]+d

Barr = np.load('/work/baseline_sst.npy'); T = np.load('/work/target_sst.npy')
tstr = np.load('/work/target_datestr.npy')
ext_start = dt.date(1991,12,27); nd = Barr.shape[0]
cdates = [ext_start + dt.timedelta(i) for i in range(nd)]
mdoy_all = np.array([mdoy(c.year,c.month,c.day) for c in cdates])
is_baseline = np.array([(dt.date(1992,1,1) <= c <= dt.date(2002,12,31)) for c in cdates])
assert mdoy_all[0]==362 and mdoy_all[4]==366 and mdoy_all[5]==1 and mdoy_all[-1]==5   # 1991-12-27=362
print('doy sequence around boundary:', mdoy_all[:8], '... last:', mdoy_all[-3:])

thr = np.full((366,)+Barr.shape[1:], np.nan); clim = np.full_like(thr, np.nan)
pool_sizes = []
t0=time.time()
for d in range(1,367):
    if d==60: continue
    ci = np.flatnonzero(is_baseline & (mdoy_all==d))
    assert ci.size>0
    idx = np.unique(np.concatenate([np.arange(max(i-5,0), min(i+5,nd-1)+1) for i in ci]))
    pool = Barr[idx]
    pool_sizes.append((d, ci.size, idx.size))
    thr[d-1]  = np.nanquantile(pool, 0.9, axis=0, method='hazen')
    clim[d-1] = np.nanmean(pool, axis=0)
print('pools+quantiles done in', round(time.time()-t0,1),'s')
ps = np.array([p[2] for p in pool_sizes])
print('pool sizes: min', ps.min(), 'max', ps.max(), 'mean', round(ps.mean(),1))
print('day-59 pool size:', dict(pool_sizes)[59], '| day-61:', dict(pool_sizes)[61])

feb29_idx = np.flatnonzero([(c.month==2 and c.day==29) for c in cdates])
print('Feb29 candidate days:', [str(cdates[i]) for i in feb29_idx])
ci59 = np.flatnonzero(is_baseline & (mdoy_all==59)); w59=set()
for i in ci59: w59.update(range(max(i-5,0), min(i+5,nd-1)+1))
ci61 = np.flatnonzero(is_baseline & (mdoy_all==61)); w61=set()
for i in ci61: w61.update(range(max(i-5,0), min(i+5,nd-1)+1))
print('all Feb29 in d59 pool:', all(i in w59 for i in feb29_idx), '| in d61 pool:', all(i in w61 for i in feb29_idx))

thr[59] = 0.5*(thr[58]+thr[60]); clim[59] = 0.5*(clim[58]+clim[60])
print('day60 = mean(d59,d61) done')

def smooth31(a):
    p = np.concatenate([a[-15:], a, a[:15]], axis=0)
    c = np.cumsum(p, axis=0)
    s = c[30:].copy(); s[1:] = c[30:] - c[:-31]
    return s/31.0
thr_s = smooth31(thr); clim_s = smooth31(clim)
chk = np.concatenate([thr[351:], thr[:15]]).mean(axis=0)
print('wrap check thr_s[365] == mean(d352..d366,1..15):', np.allclose(thr_s[365], chk))

sea = np.isfinite(T).all(axis=0)
print('sea cells:', sea.sum())
print('sea-cell baseline NaN days max:', np.isnan(Barr[:,sea]).sum(axis=0).max())
print('NaNs in thr_s/clim_s on sea cells:', np.isnan(thr_s[:,sea]).sum(), np.isnan(clim_s[:,sea]).sum())

tdoy = np.array([mdoy(int(s[:4]),int(s[4:6]),int(s[6:])) for s in tstr])
print('target doys:', tdoy[0], '->', tdoy[-1], 'contig:', np.all(np.diff(tdoy)==1))
hot = np.zeros(T.shape, bool)
for t in range(T.shape[0]):
    hot[t] = T[t] >= thr_s[tdoy[t]-1]
print('hot day-cells (sea):', int(hot[:,sea].sum()), '=', round(hot[:,sea].sum()/(sea.sum()*92)*100,2), '%')
np.save('/work/thr_s.npy', thr_s); np.save('/work/clim_s.npy', clim_s); np.save('/work/hot.npy', hot)
np.save('/work/sea.npy', sea)
print('sample cell (30,30): sea', sea[30,30], 'T Jun1-5:', T[:5,30,30].round(2),
      'thr d153-157:', thr_s[152:157,30,30].round(2), 'clim:', clim_s[152:157,30,30].round(2))
