import numpy as np, datetime as dt, time
import warnings; warnings.filterwarnings('ignore')
t0 = time.time()
S_base = np.load('/work/S_base.npy'); S_tgt = np.load('/work/S_tgt.npy').reshape(92,-1)
cr = np.load('/work/coords.npz')
base_dates = [dt.date.fromisoformat(str(d)) for d in cr['baseline_dates'].astype('datetime64[D]').astype(object)]
tgt_doy = np.load('/work/tgt_doy.npy')
sea_cells = np.load('/work/sea_cells.npy')

def doy(d):
    cum=[0]
    for L in [31,29,31,30,31,30,31,31,30,31,30,31]: cum.append(cum[-1]+L)
    return cum[d.month-1]+d.day
base_doy = np.array([doy(d) for d in base_dates])
date_to_idx = {d:i for i,d in enumerate(base_dates)}

def pool_idx(d):
    idxs = []
    for y in range(1992, 2003):
        b = None
        for cand in [dt.date(y,1,1)+dt.timedelta(days=k) for k in range(370)]:
            if cand.year == y and doy(cand) == d:
                b = cand; break
        for k in range(-5,6):
            idxs.append(date_to_idx[b + dt.timedelta(days=k)])
    return idxs

def hazen_p90(X):
    Y = np.where(np.isfinite(X), X, np.inf)
    Ys = np.sort(Y, axis=0)
    n = np.isfinite(Ys).sum(axis=0)
    NC = X.shape[1]
    out = np.full(NC, np.nan)
    okm = n > 0
    nn = n[okm].astype(float)
    h = nn*0.9 + 0.5
    j = np.floor(h).astype(int)
    frac = h - j
    Ysok = Ys[:, okm]
    m = Ysok.shape[1]
    a = Ysok[j-1, np.arange(m)]
    b = Ysok[j, np.arange(m)]
    q = (1-frac)*a + frac*b
    out[okm] = q
    return out

td = np.unique(tgt_doy)
thr_manual = np.full((366, 3600), np.nan)
for d in td:
    X = S_base[pool_idx(int(d))].reshape(-1, 3600)
    thr_manual[d-1] = hazen_p90(X)
print("manual thr done", time.time()-t0)

b_idx_by_doy = {}
for i, d in enumerate(base_dates):
    if dt.date(1992,1,1) <= d <= dt.date(2002,12,31):
        b_idx_by_doy.setdefault(base_doy[i], []).append(i)
pool_mask = np.zeros((367, len(base_dates)), dtype=bool)
for d in range(1, 367):
    if d == 60: continue
    for bi in b_idx_by_doy[d]:
        b = base_dates[bi]
        for k in range(-5, 6):
            pool_mask[d, date_to_idx[b + dt.timedelta(days=k)]] = True
thr_pipe = np.full((366, 3600), np.nan)
for d in td:
    X = S_base[pool_mask[int(d)]].reshape(-1, 3600)
    thr_pipe[d-1] = np.nanquantile(X, 0.9, method='hazen', axis=0)
print("pipeline raw thr done", time.time()-t0)

diff = np.abs(thr_manual - thr_pipe)
print("max |manual - pipeline| raw thr, target doys, all cells:", np.nanmax(diff))
print("NaN agreement:", bool((~np.isfinite(thr_manual) == ~np.isfinite(thr_pipe)).all()))

thr_pipe[59] = 0.5*(thr_pipe[58]+thr_pipe[60])
idxw = (np.arange(366)[:, None] + (-15 + np.arange(31))[None, :]) % 366
thr_s_pipe = thr_pipe[idxw].mean(axis=1)
saved_thr_s = np.load('/work/thr_s.npy')
print("max |smoothed recompute - saved thr_s| on target doys:", np.nanmax(np.abs(thr_s_pipe - saved_thr_s)[td]))

hot_manual = S_tgt >= thr_s_pipe[tgt_doy]
print("hot cell-days (manual chain):", int(hot_manual.sum()))
np.save('/work/thr_s_pipecheck.npy', thr_s_pipe)
print("CROSS-CHECK DONE", time.time()-t0)
