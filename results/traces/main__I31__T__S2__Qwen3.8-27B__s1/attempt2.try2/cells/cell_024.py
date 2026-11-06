import numpy as np
from datetime import date, timedelta

z = np.load('/work/stats.npz', allow_pickle=False)
thr = z['thr']; t_dates = z['t_dates']
zz = np.load('/work/read_done.npz', allow_pickle=False)
tgt = zz['tgt'].astype(np.float64)
base = zz['base']; b_dates = zz['b_dates']
La, Lo = 60, 60
la, lo = 40, 5
c = la*Lo + lo

# independent threshold computation for this cell
def independent_thr_cell(bdates, bvals, target_doy):
    # bvals: (nB,) float64 with NaN
    bidx = {np.datetime64(d,'D'): k for k, d in enumerate(bdates)}
    md = {}
    for d in range(1, 367):
        dt = date(2000,1,1) + timedelta(days=d-1)
        md[d] = (dt.month, dt.day)
    raw = {}
    for d in range(1, 367):
        if d == 60: continue
        m, dd = md[d]
        dates = set()
        for y in range(1992, 2003):
            b = date(y, m, dd)
            for k in range(-5, 6):
                t = np.datetime64(b + timedelta(days=k), 'D')
                if t in bidx: dates.add(bidx[t])
        pool = bvals[np.array(sorted(dates))]
        pool = pool[~np.isnan(pool)]
        n = len(pool)
        if n == 0:
            raw[d] = (np.nan, np.nan); continue
        p = np.sort(pool)
        h = n*0.9 - 0.5          # hazen (Hyndman-Fan type 5), 0-based, clamped
        h = min(max(h, 0.0), n-1)
        j = int(h); g = h - j
        q = p[j] if g < 1e-15 or j >= n-1 else p[j] + g*(p[j+1]-p[j])
        raw[d] = (q, pool.mean())
    raw[60] = ((raw[59][0]+raw[61][0])/2, (raw[59][1]+raw[61][1])/2)
    arr = np.array([raw[d][0] for d in range(1,367)])
    sm = np.array([np.mean([(arr[(d + k - 1) % 366]) for k in range(-15, 16)]) for d in range(366)])
    return sm

sm_indep = independent_thr_cell(b_dates, base[:, la, lo].astype(np.float64), None)
doy_t = np.array([t_dates[k].astype(object).timetuple().tm_yday for k in range(len(t_dates))], dtype=int)
diff = np.abs(sm_indep - thr[c])
print("max |independent - stored| thr for cell(40,5):", diff.max())

# exact margins around Jun 17-27
print("\ncell(40,5) exact (K):")
for k in range(16, 27):
    s = tgt[k, la, lo]; th = thr[c, doy_t[k]]
    print(f"{str(t_dates[k])[:10]} doy={doy_t[k]} sst={s!r} thr={th!r} hot={s >= th} margin={s-th:+.4f}")
