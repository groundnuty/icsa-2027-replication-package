import numpy as np, json
z = np.load('/work/stats.npz', allow_pickle=False)
thr = z['thr']; t_dates = z['t_dates']
zz = np.load('/work/read_done.npz', allow_pickle=False)
base = zz['base']; b_dates = zz['b_dates']
La, Lo = 60, 60
C = La*Lo

# baseline subset: 1992-01-01..2002-12-31
from datetime import date
i0 = int((np.datetime64('1992-01-01','D') - np.datetime64('1991-12-27','D'))/np.timedelta64(1,'D'))
i1 = int((np.datetime64('2002-12-31','D') - np.datetime64('1991-12-27','D'))/np.timedelta64(1,'D'))
b_base = base[i0:i1+1].astype(np.float64)
doy_base = np.array([b_dates[k].astype(object).timetuple().tm_yday for k in range(i0, i1+1)], dtype=int)
sea_flat = np.isfinite(zz['tgt']).all(axis=0).reshape(-1)
hotc = 0; totc = 0
for c in range(C):
    if not sea_flat[c]: continue
    la, lo = divmod(c, Lo)
    s = b_base[:, la, lo]
    th = thr[c, doy_base]
    m = np.isfinite(s) & np.isfinite(th)
    hotc += int((s[m] >= th[m]).sum()); totc += int(m.sum())
print(f"baseline 'hot' fraction (calibration check, expect ~10%): {hotc/totc*100:.2f}%  ({hotc}/{totc})")

# how many baseline years have MHWs in the region? (context)
def true_runs(x):
    n = len(x)
    d = np.diff(x.astype(np.int8))
    s = np.where(d == 1)[0] + 1; e = np.where(d == -1)[0] + 1
    if x[0]: s = np.concatenate(([0], s))
    if x[-1]: e = np.concatenate((e, [n]))
    return s, e
def cell_mhw(h, Tn):
    inm = np.zeros(Tn, bool)
    s_, e_ = true_runs(np.concatenate(([False], h, [False])))
    for a, b in zip(s_, e_):
        if b - a >= 5: inm[a:b] = True
    gs, ge = true_runs(np.concatenate(([True], ~inm, [True])))
    for a, b in zip(gs, ge):
        if b - a in (1, 2) and a > 0 and inm[a-1] and b < Tn and inm[b]:
            inm[a:b] = True
    return inm
for yr in range(1992, 2003):
    m = np.array([b_dates[k].astype(object).year == yr for k in range(i0, i1+1)])
    n = int(m.sum())
    ev = 0
    for c in range(0, C, 37):   # subsample cells for speed
        if not sea_flat[c]: continue
        la, lo = divmod(c, Lo)
        s = b_base[m, la, lo]
        if not np.isfinite(s).all(): continue
        h = s >= thr[c, doy_base[m]]
        if cell_mhw(h, n).any(): ev += 1
    print(f"1992-2002 {yr}: subsampled cells with any MHW day: {ev}")
