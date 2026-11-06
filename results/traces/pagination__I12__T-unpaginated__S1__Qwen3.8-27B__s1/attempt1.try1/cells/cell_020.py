import numpy as np, datetime as dt
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
    dates = []
    for y in range(1992, 2003):
        anch = dt.date(y, md[0], md[1])
        dates.extend(anch + dt.timedelta(days=k) for k in range(-5, 6))
    return dates

for doy in (183, 153, 244, 59, 61, 1):
    pd = pool_dates(doy)
    vals = col[[brow[x] for x in pd]]
    assert np.isfinite(vals).all()
    vs = np.sort(vals)
    n = len(vs)
    h = (n-1)*0.90 + 1
    lo = int(np.floor(h-1)); frac = (h-1) - lo
    q_manual = vs[lo] + frac*(vs[min(lo+1, n-1)] - vs[lo])
    m_manual = vals.mean()
    print(f'doy {doy}: n={n} {pd[0]}..{pd[-1]} | thr match={q_manual==thr_raw[doy-1,c]} ({q_manual:.9f} vs {thr_raw[doy-1,c]:.9f}) | clim match={m_manual==clim_raw[doy-1,c]}')