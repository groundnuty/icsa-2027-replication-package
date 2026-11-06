import numpy as np, xarray as xr, json, os, warnings
warnings.filterwarnings('ignore')

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
lat = ds['latitude'].values; lon = ds['longitude'].values
tv = ds['time'].values
d64 = tv.astype('datetime64[D]')
print('enc:', {k: ds['analysed_sst'].encoding.get(k) for k in ('_FillValue','scale_factor','add_offset')})
print('units:', ds['analysed_sst'].attrs.get('units'))
print('time gaps:', np.unique(np.diff(d64.astype(np.int64))))

# fixed 366-day calendar: Jan1=1 ... Feb28=59, Feb29=60, Mar1=61 ... Dec31=366
off = np.array([0,31,60,91,121,152,182,213,244,274,305,335])
months = (d64.astype('datetime64[M]').astype(np.int64) % 12) + 1
days = (d64 - d64.astype('datetime64[M]')).astype(np.int64) + 1
tdoy = off[months-1] + days
print('tdoy checks:', tdoy[np.where(d64==np.datetime64('2000-02-29'))[0][0]],
      tdoy[np.where(d64==np.datetime64('2001-12-31'))[0][0]],
      tdoy[np.where(d64==np.datetime64('2015-06-01'))[0][0]])

latf = lat.astype('float64'); lonf = lon.astype('float64')
ii = np.where((latf >= 56.13) & (latf <= 57.33))[0]
jj = np.where((lonf >= 17.71) & (lonf <= 18.91))[0]
print('region idx lat', ii[0], ii[-1], 'lon', jj[0], jj[-1], '->', len(ii), 'x', len(jj))

t0 = d64[0]
def ix(y,m,d):
    k = int((np.datetime64(f'{y:04d}-{m:02d}-{d:02d}') - t0).astype(np.int64))
    assert d64[k] == np.datetime64(f'{y:04d}-{m:02d}-{d:02d}'), (y,m,d)
    return k
lo, hi = ix(1991,12,26), ix(2003,1,6)
blo, bhi = ix(1992,1,1), ix(2002,12,31)
glo, ghi = ix(2015,6,1), ix(2015,8,31)
assert np.all(np.diff(d64[lo:hi+1].astype(np.int64)) == 1)
assert np.all(np.diff(d64[glo:ghi+1].astype(np.int64)) == 1)
print('baseline span used: 1991-12-27 .. 2003-01-05 -> block loaded 1991-12-26..2003-01-06')

sl = dict(latitude=slice(ii[0], ii[-1]+1), longitude=slice(jj[0], jj[-1]+1))
b = ds['analysed_sst'].isel(time=slice(lo, hi+1), **sl).values.astype('float64')
print('base block', b.shape, 'finite frac', round(float(np.isfinite(b).mean()),4))
tgt = ds['analysed_sst'].isel(time=slice(glo, ghi+1), **sl).values.astype('float64')
print('target block', tgt.shape)

flat = b.reshape(b.shape[0], -1)
bpos = np.arange(blo - lo, bhi - lo + 1)
bdoy = tdoy[blo:bhi+1]
print('baseline days', len(bpos), 'doy60 count', int((bdoy==60).sum()))

thr = np.full((366, flat.shape[1]), np.nan)
clim = np.full_like(thr, np.nan)
psizes = []
for d in range(1, 367):
    if d == 60: continue
    pp = np.unique(np.concatenate([np.arange(p-5, p+6) for p in bpos[bdoy == d]]))
    psizes.append(len(pp))
    blk = flat[pp]
    thr[d-1] = np.nanquantile(blk, 0.9, axis=0, method='hazen')
    clim[d-1] = np.nanmean(blk, axis=0)
print('pool sizes min/max:', min(psizes), max(psizes))
thr[59] = 0.5*(thr[58] + thr[60]); clim[59] = 0.5*(clim[58] + clim[60])
w = (np.arange(366)[:,None] + np.arange(-15,16)[None,:]) % 366
thr_s = thr[w].mean(axis=1); clim_s = clim[w].mean(axis=1)
np.save('/work/thr_s.npy', thr_s); np.save('/work/clim_s.npy', clim_s)

tflat = tgt.reshape(tgt.shape[0], -1)
t_doy = tdoy[glo:ghi+1]
print('target doys', t_doy[0], '..', t_doy[-1], 'n=', len(t_doy))
sea = np.isfinite(tflat).all(axis=0)
fin_any = np.isfinite(tflat).any(axis=0)
print('cells:', tflat.shape[1], 'sea:', int(sea.sum()), 'all-nan:', int((~fin_any).sum()), 'partial:', int((fin_any & ~sea).sum()))
np.save('/work/sea.npy', sea)

hot = tflat >= thr_s[t_doy - 1]
hot[:, ~sea] = False
T, C = hot.shape
pad = np.zeros((T+2, C), np.int8); pad[1:-1] = hot
dif = np.diff(pad, axis=0)
s_rc = np.argwhere(dif == 1); e_rc = np.argwhere(dif == -1)
so = s_rc[np.lexsort((s_rc[:,0], s_rc[:,1]))]
eo = e_rc[np.lexsort((e_rc[:,0], e_rc[:,1]))]
assert (so[:,1] == eo[:,1]).all()
st, en, cl = so[:,0], eo[:,0], so[:,1]
keep = (en - st) >= 5
print('runs >=5 hot days:', int(keep.sum()))
merged = []
for s_, e_, c_ in zip(st[keep], en[keep], cl[keep]):
    if merged and merged[-1][2] == c_ and s_ - merged[-1][1] <= 2:
        merged[-1][1] = e_
    else:
        merged.append([s_, e_, int(c_)])
print('per-cell MHWs after joining:', len(merged))
mask = np.zeros((T, C), np.uint8)
for s_, e_, c_ in merged:
    mask[s_:e_, c_] = 1
active = mask.any(axis=1)
print('active days:', int(active.sum()), 'of', T)
events = []
i = 0
while i < T:
    if active[i]:
        j = i
        while j+1 < T and active[j+1]: j += 1
        events.append((i, j)); i = j+1
    else:
        i += 1
dstr = lambda k: str(d64[glo + k])
ev_out = [{'onset': dstr(a), 'end': dstr(bb)} for a, bb in events]
print('regional events:', ev_out)
durs = [e_-s_ for s_,e_,_ in merged]
print('cell-MHW duration min/med/max:', min(durs), float(np.median(durs)), max(durs))
percell = np.bincount([c_ for _,_,c_ in merged], minlength=C)
print('sea cells with >=1 MHW:', int((percell>0).sum()), '/', int(sea.sum()))
c0 = merged[0][2]
print('sample sea cell thr_s[152:162]:', np.round(thr_s[152:162],3))
print('sample sea cell clim_s[152:162]:', np.round(clim_s[152:162],3))
print('sample cell SST 2015-06-01..05:', np.round(tflat[:5, c0],3))
np.savez('/work/diag.npz', mask=mask.reshape(T, len(ii), len(jj)), active=active, t_doy=t_doy)
