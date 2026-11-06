import numpy as np, datetime as dt
a = np.load('/tmp/base_a.npz'); b = np.load('/tmp/base_b.npz')
base = np.concatenate([a['arr'], b['arr']], axis=0)
bdates = [dt.date.fromisoformat(s) for s in np.concatenate([a['dates'], b['dates']])]
brow = {d: i for i, d in enumerate(bdates)}
thr_raw = np.load('/tmp/thr_raw.npy'); clim_raw = np.load('/tmp/clim_raw.npy')

def pool_dates(doy):
    d = dt.date(2000,1,1)
    while d.year == 2000:
        if d.timetuple().tm_yday == doy:
            md = (d.month, d.day); break
        d += dt.timedelta(days=1)
    out = []
    for y in range(1992, 2003):
        anch = dt.date(y, md[0], md[1])
        out.extend(anch + dt.timedelta(days=k) for k in range(-5, 6))
    return out

allmatch = True
for c in (3260, 0, 1000, 3599-0, 1234, 3000):
    col = base.reshape(4028, 3600)[:, c]
    for doy in (153, 183, 244, 59, 61, 1, 366, 200):
        pd = pool_dates(doy)
        vals = col[[brow[x_] for x_ in pd]]
        vs = np.sort(vals); n = len(vs)
        vi = n*0.90 - 0.5           # 0-based virtual index (numpy hazen)
        lo = int(np.floor(vi)); frac = vi - lo
        q = vs[lo] + frac*(vs[min(lo+1, n-1)] - vs[lo])
        ok = (q == thr_raw[doy-1, c]) and (vals.mean() == clim_raw[doy-1, c])
        allmatch &= ok
        if not ok:
            print('MISMATCH cell', c, 'doy', doy, q, thr_raw[doy-1, c], vals.mean(), clim_raw[doy-1,c])
print('all manual checks pass:', bool(allmatch))
# also confirm nanquantile path equals quantile path on finite data for one pool
vals = col[[brow[x_] for x_ in pool_dates(183)]]
print('nanquantile==quantile on finite pool:',
      np.nanquantile(vals, 0.9, method='hazen') == np.quantile(vals, 0.9, method='hazen'))