import numpy as np
x = np.arange(1, 11, dtype=float)
for m in ('hazen', 'weibull', 'linear', 'median_unbiased', 'normal_unbiased'):
    print(m, np.quantile(x, 0.25, method=m))
# for n=10: hazen h=(n+1)p=2.75 -> 2.75; type5 h=(n+.5)p+.5=3.125; linear 3.25
# now re-verify pools with the hazen formula h=(n+1)*p
import datetime as dt
a = np.load('/tmp/base_a.npz'); b = np.load('/tmp/base_b.npz')
base = np.concatenate([a['arr'], b['arr']], axis=0)
bdates = [dt.date.fromisoformat(s) for s in np.concatenate([a['dates'], b['dates']])]
brow = {d: i for i, d in enumerate(bdates)}
thr_raw = np.load('/tmp/thr_raw.npy'); clim_raw = np.load('/tmp/clim_raw.npy')
c = 3260
col = base.reshape(4028, 3600)[:, c]
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
for doy in (183, 153, 244, 59, 61, 1, 366):
    pd = pool_dates(doy)
    vals = col[[brow[x_] for x_ in pd]]
    vs = np.sort(vals); n = len(vs)
    h = (n+1)*0.90          # hazen position, 1-based
    lo = int(np.floor(h-1)); frac = (h-1) - lo
    q = vs[lo] + frac*(vs[min(lo+1, n-1)] - vs[lo])
    print(f'doy {doy}: n={n} h={h} hazen-manual match={q==thr_raw[doy-1,c]}  ({q:.9f} vs {thr_raw[doy-1,c]:.9f})')