import numpy as np
from datetime import date

z = np.load('/work/stats.npz', allow_pickle=False)
thr = z['thr']; clim = z['clim']; t_dates = z['t_dates']
zz = np.load('/work/read_done.npz', allow_pickle=False)
base = zz['base']; b_dates = zz['b_dates']
tgt = zz['tgt'].astype(np.float64)
T, La, Lo = tgt.shape
C = La * Lo
doy_t = np.array([t_dates[k].astype(object).timetuple().tm_yday for k in range(T)], dtype=int)

# correct indexing: doy d -> index d-1
thrT = thr[:, doy_t - 1]                       # (C, T)

sea_flat = np.isfinite(tgt).all(axis=0).reshape(-1)
hot = np.zeros((C, T), bool)
for c in range(C):
    if not sea_flat[c]: continue
    la, lo = divmod(c, Lo)
    hot[c] = tgt[:, la, lo] >= thrT[c]
print("hot cell-days (corrected):", int(hot.sum()))

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

maxrun = np.zeros(C, int)
for c in range(C):
    if not sea_flat[c]: continue
    s, e = true_runs(hot[c])
    if len(s): maxrun[c] = (e - s).max()
print("max hot run:", maxrun.max(), " cells with run>=5:", int((maxrun>=5).sum()), " >=4:", int((maxrun>=4).sum()))

# cell (40,5) margins with corrected indexing
la, lo, c = 40, 5, 40*60+5
print("\ncell(40,5) corrected margins:")
for k in range(15, 28):
    s = tgt[k, la, lo]; th = thr[c, doy_t[k]-1]
    print(f"{str(t_dates[k])[:10]} doy={doy_t[k]} sst={s:.4f} thr={th:.4f} hot={s>=th} margin={s-th:+.4f}")

# baseline calibration: fraction of baseline cell-days above their (correct) threshold
i0 = int((np.datetime64('1992-01-01','D') - np.datetime64('1991-12-27','D'))/np.timedelta64(1,'D'))
i1 = int((np.datetime64('2002-12-31','D') - np.datetime64('1991-12-27','D'))/np.timedelta64(1,'D'))
b_base = base[i0:i1+1].astype(np.float64)
doy_base = np.array([b_dates[k].astype(object).timetuple().tm_yday for k in range(i0, i1+1)], dtype=int)
hotc = totc = 0
for c in range(C):
    if not sea_flat[c]: continue
    la, lo = divmod(c, Lo)
    s = b_base[:, la, lo]; th = thr[c, doy_base - 1]
    m = np.isfinite(s) & np.isfinite(th)
    hotc += int((s[m] >= th[m]).sum()); totc += int(m.sum())
print(f"\nbaseline hot fraction (expect ~10%): {hotc/totc*100:.2f}%  ({hotc}/{totc})")

np.savez('/work/hot_correct.npz', hot=hot, sea_flat=sea_flat, t_dates=t_dates,
         lat_vals=z['lat_vals'], lon_vals=z['lon_vals'], thrT=thrT)
print("saved hot_correct.npz")
