import numpy as np, datetime as dt, time, warnings, json

t0=time.time()
def build(y0,m0,d0,y1,m1,d1):
    a=dt.date(y0,m0,d0); b=dt.date(y1,m1,d1)
    return [a+dt.timedelta(days=i) for i in range((b-a).days+1)]
ext = build(1991,12,27,2003,1,5)
tgt = build(2007,6,1,2007,8,31)
ext_s = [d.strftime('%Y%m%d') for d in ext]
tgt_s = [d.strftime('%Y%m%d') for d in tgt]

def load_stack(ds_):
    out = np.empty((len(ds_),60,60), dtype='float64')
    for i,d in enumerate(ds_):
        out[i] = np.load(f'cache/arr/{d}.npy')
    return out
SST = load_stack(ext_s); SST_t = load_stack(tgt_s)
print('loaded', SST.shape, SST_t.shape, f'{time.time()-t0:.1f}s', flush=True)

cum = [0,31,60,91,121,152,182,213,244,274,305,335]
def mdoy(y,m,d): return cum[m-1]+d
doy_ext = np.array([mdoy(d.year,d.month,d.day) for d in ext])
doy_tgt = np.array([mdoy(d.year,d.month,d.day) for d in tgt])
print('target doys', doy_tgt[0],'..',doy_tgt[-1])
orid = np.array([d.toordinal() for d in ext])

sea = np.isfinite(SST_t).all(axis=0)
print('sea cells:', int(sea.sum()), 'of', sea.size)
print('baseline NaN frac over all cells:', float(np.isnan(SST).mean()))
print('baseline NaNs in sea cells:', int(np.isnan(SST[:,sea]).sum()), 'of', SST[:,sea].size)

clim_raw = np.full((366,60,60), np.nan)
thr_raw  = np.full((366,60,60), np.nan)
counts = np.zeros(366, dtype=int)
with warnings.catch_warnings():
    warnings.simplefilter('ignore', RuntimeWarning)
    for doy in range(1,367):
        if doy==60: continue
        m,d = inv_ = None, None
        # inverse mapping
        for mm in range(1,13):
            if 1 <= doy-cum[mm-1] <= (29 if mm==2 else [31,28,31,30,31,30,31,31,30,31,30,31][mm-1] if mm!=2 else 29):
                m, dd = mm, doy-cum[mm-1]; break
        anchors = np.array([dt.date(Y,m,dd).toordinal() for Y in range(1992,2003)])
        dist = np.min(np.abs(orid[:,None]-anchors[None,:]),axis=1)
        sel = dist<=5
        counts[doy-1] = int(sel.sum())
        pool = SST[sel]
        clim_raw[doy-1] = np.nanmean(pool, axis=0)
        thr_raw[doy-1]  = np.nanquantile(pool, 0.9, axis=0, method='hazen')
print('pool sizes:', sorted(set(counts[0:59].tolist()+counts[60:].tolist())), f'{time.time()-t0:.1f}s', flush=True)

clim = clim_raw.copy(); thr = thr_raw.copy()
clim[59] = 0.5*(clim_raw[58]+clim_raw[60])
thr[59]  = 0.5*(thr_raw[58]+thr_raw[60])

ar = np.arange(366)
def circ31(V):
    out = np.zeros_like(V)
    for off in range(-15,16):
        out += V[(ar+off)%366]
    return out/31.0
clim_s = circ31(clim); thr_s = circ31(thr)
print('smoothed. clim_s finite over sea:', bool(np.isfinite(clim_s[:,sea]).all()),
      '| thr_s finite over sea:', bool(np.isfinite(thr_s[:,sea]).all()), f'{time.time()-t0:.1f}s', flush=True)

np.save('cache/clim_s.npy', clim_s); np.save('cache/thr_s.npy', thr_s)
np.save('cache/sea.npy', sea); np.save('cache/SST_t.npy', SST_t)
json.dump({'ext_s':ext_s,'tgt_s':tgt_s}, open('cache/dates.json','w'))
print('done, total', f'{time.time()-t0:.1f}s')
