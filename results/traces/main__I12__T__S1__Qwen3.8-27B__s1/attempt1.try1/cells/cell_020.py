import numpy as np, datetime as dt
z = np.load('data/climthr.npz')
thr_raw, sea, tgt_doy = z['thr_raw'], z['sea'], z['tgt_doy']
SST_win = np.load('data/SST_win.npy'); SST_tgt = np.load('data/SST_tgt.npy')
res = np.load('data/results.npz')
mhw_main = res['mhw']

# rebuild pools (same idx scheme) but with method='linear' (HF type 4, true MATLAB default)
def daterange(a, b):
    d = a
    while d <= b:
        yield d; d += dt.timedelta(days=1)
win_dates = list(daterange(dt.date(1991,12,27), dt.date(2003,1,5)))
base_start = dt.date(1992,1,1); base_end = dt.date(2002,12,31)
def doy(d): return (d.replace(year=2000) - dt.date(2000,1,1)).days + 1
anchor = {}
for i, wdt in enumerate(win_dates):
    if base_start <= wdt <= base_end:
        anchor.setdefault(doy(wdt), []).append(i)
thr_lin = np.full((366, 60, 60), np.nan)
for d, alist in anchor.items():
    if d == 60: continue
    idx = np.concatenate([np.arange(a-5, a+6) for a in sorted(alist)])
    thr_lin[d-1] = np.nanquantile(SST_win[idx], 0.9, axis=0, method='linear')
thr_lin[59] = (thr_lin[58] + thr_lin[60]) / 2.0
x = thr_lin
x_ext = np.concatenate([x[-15:], x, x[:15]], axis=0)
c = np.concatenate([np.zeros((1,60,60)), np.cumsum(x_ext, axis=0)], axis=0)
thr_lin_s = (c[31:397] - c[0:366]) / 31.0

hot_lin = (SST_tgt >= thr_lin_s[tgt_doy-1]) & sea
def detect(hot):
    N = hot.shape[0]
    mhw = np.zeros((N, 60, 60), bool)
    for cell in range(3600):
        cc, ll = divmod(cell, 60)
        if not sea[cc, ll]: continue
        h = hot[:, cc, ll]
        runs, i = [], 0
        while i < N:
            if h[i]:
                j = i
                while j+1 < N and h[j+1]: j += 1
                runs.append([i, j]); i = j+1
            else: i += 1
        runs = [r for r in runs if r[1]-r[0]+1 >= 5]
        merged = []
        for s, e in runs:
            if merged and s - merged[-1][1] - 1 <= 2:
                merged[-1][1] = e
            else:
                merged.append([s, e])
        for s, e in merged:
            mhw[s:e+1, cc, ll] = True
    return mhw

mhw_lin = detect(hot_lin)
mhw_haz = mhw_main.astype(bool)
print('mask equal (hazen vs linear):', np.array_equal(mhw_haz, mhw_lin))
print('cells differing:', (mhw_haz != mhw_lin).any(axis=0).sum())
act_lin = mhw_lin.any(axis=(1,2)); act_haz = mhw_haz.any(axis=(1,2))
print('active days equal:', np.array_equal(act_lin, act_haz))
for name, act in (('hazen', act_haz), ('linear', act_lin)):
    ev = []
    i = 0
    while i < 92:
        if act[i]:
            j = i
            while j+1 < 92 and act[j+1]: j += 1
            ev.append((i, j)); i = j+1
        else: i += 1
    dates = list(daterange(dt.date(2009,6,1), dt.date(2009,8,31)))
    print(name, 'events:', [(dates[s], dates[e]) for s, e in ev])
# how big is the threshold difference typically / for target doys
diff = np.abs(thr_lin_s[tgt_doy-1] - z['thr_smooth'][tgt_doy-1])
print('thr diff (lin vs haz) over target: max %.4f K, mean %.4f K' % (diff.max(), diff.mean()))