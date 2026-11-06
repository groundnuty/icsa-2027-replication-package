
import numpy as np, pandas as pd
X = np.load('/tmp/mhw/ext.npy'); Y = np.load('/tmp/mhw/tgt.npy')
ed = pd.to_datetime(np.load('/tmp/mhw/ext_dates.npy'), unit='D')
td = pd.to_datetime(np.load('/tmp/mhw/tgt_dates.npy'), unit='D')
in_mhw = np.load('/tmp/mhw/in_mhw.npy')
evs = np.load('/tmp/mhw/evs.npy', allow_pickle=True)

cum = np.array([0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335])
doy_ext = cum[np.asarray(ed.month)-1] + np.asarray(ed.day)
def hf5(x, p):
    x = np.sort(x); n = len(x)
    h = (np.arange(1, n+1) - 0.5) / n
    return float(np.interp(p, h, x))
b0, b1 = 5, 4023
c = 1230
thr_c = np.full(366, np.nan)
with np.errstate(all='ignore'):
    for d in range(1, 367):
        if d == 60: continue
        p = b0 + np.flatnonzero(doy_ext[b0:b1] == d)
        pp = np.concatenate([np.arange(p0-5, p0+6) for p0 in p])
        v = X[pp, c]; v = v[np.isfinite(v)]
        thr_c[d-1] = hf5(v, 0.9) if len(v) else np.nan
thr_c[59] = 0.5*(thr_c[58] + thr_c[60])
sm5 = float(np.nanmean(thr_c[(np.arange(5-15, 5+16)) % 366]))
manual5 = float(np.nanmean(np.concatenate([thr_c[355:366], thr_c[0:20]])))
print("wrap check doy5: code %.6f manual %.6f match: %s" % (sm5, manual5, sm5 == manual5))

active = in_mhw.any(axis=1)
act_days = [str(td[i].date()) for i in range(92) if active[i]]
print("active days:", len(act_days), "first:", act_days[0], "last:", act_days[-1])
inactive = [str(td[i].date()) for i in range(92) if not active[i]]
print("inactive days:", inactive)
print("events saved:", [tuple(e) for e in evs])
durs = in_mhw.sum(axis=0)
print("cells with any MHW day:", int((durs>0).sum()), "max dur:", int(durs.max()), "min dur (nonzero):", int(durs[durs>0].min()))
