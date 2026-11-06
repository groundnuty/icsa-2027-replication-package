import numpy as np
import pickle
import time as _time

with open('/work/data.pkl','rb') as f:
    D = pickle.load(f)
V_win = D['V_win']      # (4028,60,60) 1991-12-27..2003-01-05
V_tgt = D['V_tgt']      # (92,60,60)  2013-06-01..2013-08-31
tw = D['time_win'].astype('datetime64[D]')
tt = D['time_tgt'].astype('datetime64[D]')

# ---- day-of-year mapping (leap-year convention: Feb29=60, Mar1=61, ... Dec31=366) ----
from datetime import date
LEAP = 2000
md2doy = {}
for m in range(1,13):
    import calendar
    for dd in range(1, calendar.monthrange(LEAP, m)[1]+1):
        md2doy[(m,dd)] = (date(LEAP,m,dd) - date(LEAP,1,1)).days + 1
def doys_of(t64):
    y = t64.astype('int64') // 10000  # works for our range; safer: use .astype('M8[Y]')...
    # proper extraction
    yrs = t64.astype('datetime64[Y]').astype(int) + 1970
    mons = t64.astype('datetime64[M]').astype(int) - (t64.astype('datetime64[Y]').astype(int) - 1969)*12
    days = t64.astype('datetime64[D]').astype(int) - (t64.astype('datetime64[M]').astype(int) - 1969*12)*30
    # simpler and exact: days-in-month via monthend diff
    return np.array([md2doy[(int(mo), int(dy))] for mo, dy in zip(mons, days)], dtype=int)

doy_win = doys_of(tw)
doy_tgt = doys_of(tt)
print("win doys first/last:", doy_win[0], doy_win[-1], "len", len(doy_win))
print("tgt doys first/last:", doy_tgt[0], doy_tgt[-1], "len", len(doy_tgt))
print("win dates:", str(tw[0]), str(tw[-1]), "tgt dates:", str(tt[0]), str(tt[-1]))
assert list(doy_win[:5]) == [361,362,363,364,365]  # 1991 Dec 27..31
assert list(doy_win[5:10]) == [1,2,3,4,5]
assert list(doy_win[-5:]) == [1,2,3,4,5]

# baseline dates are win indices 5..4022 inclusive
P = np.zeros(len(doy_win), dtype=int)
P[5:4023] = doy_win[5:4023]
n_base = int((P>0).sum())
print("baseline days:", n_base, " (expect 4018)")
assert n_base == 4018

# ---- pool index per doy d (d != 60): union of [j-5, j+5] over baseline j with P[j]==d ----
V2 = V_win.reshape(4028, 3600)
sea = np.all(np.isfinite(V_tgt), axis=0)
sea2 = sea.reshape(3600)
Vsea = V2[:, sea2]          # (4028, 3309)
# check: are all sea cells finite everywhere in the window?
fin_counts = np.isfinite(V2).sum(axis=0)
print("cells with any NaN in window:", (fin_counts < 4028).sum(), "min fin count:", fin_counts.min())

t0=_time.time()
K = Vsea.shape[1]
thr = np.full(367, np.nan)   # index by doy 1..366
clim = np.full(367, np.nan)
for d in range(1, 367):
    if d == 60:
        continue
    js = np.where(P == d)[0]
    assert js.size == 11, (d, js.size)
    idx = np.concatenate([np.arange(j-5, j+6) for j in js])
    assert len(idx) == 121
    pool = Vsea[:, idx]      # (3309, 121)
    thr[d] = np.nanquantile(pool, 0.90, method='hazen', axis=1)
    clim[d] = np.nanmean(pool, axis=1)
print("thresholds computed in", _time.time()-t0, "s; NaN thr cells:", int(np.isnan(thr[:, 1:]).sum(axis=1).sum()),
      "NaN clim cells:", int(np.isnan(clim[:, 1:]).sum(axis=1).sum()))
# sanity: thresholds plausible (~kelvin, summer max)
print("thr doy 180 mean/median:", thr[180].mean(), np.median(thr[180]))
print("clim doy 180 mean:", clim[180].mean())

with open('/work/thr.pkl','wb') as f:
    pickle.dump({'thr': thr, 'clim': clim, 'sea2': sea2, 'doy_tgt': doy_tgt, 'tt': D['time_tgt']}, f)
print("saved thr/clim")
