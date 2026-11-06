import numpy as np, datetime as dt, warnings
warnings.filterwarnings('ignore')

coords = np.load('/work/coords.npz', allow_pickle=True)
time_tgt = coords['time_tgt']; time_ext = coords['time_ext']
tgt64 = np.load('/work/sst_tgt.npy').astype(np.float64)
mhw = np.load('/work/mhw.npy'); sea = np.load('/work/sea.npy'); hot = np.load('/work/hot.npy')
thr = np.load('/work/thr.npy'); ext = np.load('/work/sst_ext.npy')

cum = np.array([0,31,60,91,121,152,182,213,244,274,305,335,366])  # sentinel
doy_t = np.array([cum[t.astype(dt.date).month-1] + t.astype(dt.date).day for t in time_tgt])
ext_dates = [np.datetime64(t,'D').astype(dt.date) for t in time_ext]

rng = np.random.default_rng(1)
cells = [(int(i), int(k)) for i, k in zip(rng.integers(0,60,4), rng.integers(0,60,4))]
for ci, ck in cells:
    if not sea[ci, ck]:
        print((ci,ck), 'land cell, skip'); continue
    ext_vals = ext[:, ci, ck].astype(np.float64)
    def pools(d):
        for mi in range(12):
            if cum[mi] < d <= cum[mi+1]:
                m, dd = mi+1, d-cum[mi]; break
        base = {dt.date(y,m,dd)+dt.timedelta(days=off) for y in range(1992,2003) for off in range(-5,6)}
        return [v for v,x in zip(ext_vals, ext_dates) if x in base and np.isfinite(v)]
    tr = np.full(366, np.nan)
    for d in list(range(1,60))+list(range(61,367)):
        v = np.sort(np.asarray(pools(d)))
        m_ = len(v); h = m_*0.9+0.5
        lo = max(1,min(m_,int(np.floor(h)))); hi = max(1,min(m_,int(np.ceil(h))))
        tr[d-1] = v[lo-1] + (h-lo)*(v[hi-1]-v[lo-1])
    tr[59] = 0.5*(tr[58]+tr[60])
    tr_s = np.array([np.mean([tr[(d+o)%366] for o in range(-15,16)]) for d in range(366)])
    hot_p = tgt64[:, ci, ck] >= tr_s[doy_t-1]
    print((ci,ck), 'hot identical:', bool(np.array_equal(hot_p, hot[:, ci, ck])), '| max|thr diff|:', float(np.max(np.abs(tr_s - thr[:, ci, ck]))))
