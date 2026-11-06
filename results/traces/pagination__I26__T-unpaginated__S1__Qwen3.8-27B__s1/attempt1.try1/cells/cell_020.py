import numpy as np, json, warnings
from datetime import date, timedelta
warnings.filterwarnings("ignore")

z = np.load('/work/cache/data.npz')
A_base = z['A_base'].astype(np.float64)
A_tgt  = z['A_tgt'].astype(np.float64)
dates = json.load(open('/work/cache/dates.json'))
base_dates = [date.fromisoformat(s) for s in dates['base']]
tgt_dates  = [date.fromisoformat(s) for s in dates['tgt']]
eom = [0,31,60,91,121,152,182,213,244,274,305,335,366]
doy_of = lambda d: eom[d.month-1] + d.day

# main-pipeline-style pools
base_idx = {d: i for i, d in enumerate(base_dates)}
pool_idx = {}
for d in range(1, 367):
    if d == 60: continue
    m = next(mm for mm in range(1,13) if eom[mm-1] < d <= eom[mm])
    day = d - eom[m-1]
    idx = set()
    for y in range(1992, 2003):
        b = date(y, m, day)
        for off in range(-5, 6):
            t = b + timedelta(days=off)
            if t in base_idx: idx.add(base_idx[t])
    pool_idx[d] = np.array(sorted(idx), dtype=np.int64)

thr_mp = np.full((366,3600), np.nan)
for d in range(1, 367):
    if d == 60: continue
    X = A_base[pool_idx[d]]
    thr_mp[d-1] = np.nanquantile(X, 0.9, method='hazen', axis=0).ravel()
thr_mp[59] = 0.5*(thr_mp[58]+thr_mp[60])
def smooth31(a):
    out = np.zeros_like(a)
    for j in range(-15,16): out += np.roll(a, j, axis=0)
    return out/31
thr_mp_s = smooth31(thr_mp)
doy_t = np.array([doy_of(d) for d in tgt_dates])
H_mp = A_tgt >= thr_mp_s[doy_t-1].reshape(92,60,60)

# independent-style (previous check) thresholds
thr_in = np.full((366, 3600), np.nan)
for d in range(1, 367):
    if d == 60: continue
    m = next(mm for mm in range(1,13) if eom[mm-1] < d <= eom[mm])
    day = d - eom[m-1]
    vals = []
    for y in range(1992, 2003):
        b = date(y, m, day)
        for off in range(-5, 6):
            t = b + timedelta(days=off)
            if base_dates[0] <= t <= base_dates[-1]:
                vals.append((t - base_dates[0]).days)
    X = A_base[vals]
    thr_in[d-1] = np.nanquantile(X, 0.9, method='hazen', axis=0).ravel()
thr_in[59] = 0.5*(thr_in[58]+thr_in[60])
thr_in_s = smooth31(thr_in)

print("pools identical sizes:", all(len(pool_idx[d]) in (len(A_base[[]]) and 0 or 0) for d in [1]))
diff_thr = ~np.allclose(thr_mp_s[doy_t-1].reshape(92,3600), thr_in_s[doy_t-1].reshape(92,3600), equal_nan=True)
print("thr differences in target doys:", int(diff_thr.sum()))
diff_H = H_mp.reshape(92,3600) != (A_tgt >= thr_in_s[doy_t-1].reshape(92,60,60)).reshape(92,3600)
print("H differences:", int(diff_H.sum()))
if diff_H.any():
    tt, cc = np.where(diff_H)
    print("first diff: t, cell:", tt[0], cc[0], "SST:", A_tgt[tt[0], cc[0]//60, cc[0]%60],
          "thr_mp:", thr_mp_s[doy_t[tt[0]]-1, cc[0]], "thr_in:", thr_in_s[doy_t[tt[0]]-1, cc[0]])
