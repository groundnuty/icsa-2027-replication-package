import numpy as np, pandas as pd, time
# Independent re-verification for a few cells
zb = np.load("work/baseline.npz")
V = zb["sst"].reshape(len(zb["time"]), -1)
T = pd.DatetimeIndex(zb["time"].astype("datetime64[D]"))
Tdt = T.to_numpy()
zt = np.load("work/target.npz"); sea = zt["sea"]
tc = np.load("work/thrclim.npz"); THR_sm = tc["THR"]

def doy_of(dt):
    m, d = dt.month, dt.day
    if m <= 2:
        return (dt - pd.Timestamp(dt.year, 1, 1)).days + 1
    return (pd.Timestamp(2004, m, d) - pd.Timestamp(2004, 1, 1)).days + 1

doyT = np.array([doy_of(x) for x in T])
base = (T >= pd.Timestamp("1992-01-01")) & (T <= pd.Timestamp("2002-12-31"))
baseline_dates = T[base]

def hazen90(vals):
    v = np.sort(vals)
    n = len(v)
    h = n*0.9 + 0.5 - 1
    j = int(np.floor(h)); g = h - j
    return v[j] + (g*(v[j+1]-v[j]) if j+1 < n else 0.0)

def pool_for_d(d, cell):
    # explicit: all dates t with |t - b| <= 5 for some baseline b with doy(b)==d
    vals = []
    for b in baseline_dates:
        if doy_of(b) != d: continue
        lo, hi = b - pd.Timedelta(days=5), b + pd.Timedelta(days=5)
        m = (Tdt >= lo.to_numpy()) & (Tdt <= hi.to_numpy())
        vals.extend(V[m, cell][np.isfinite(V[m, cell])].tolist())
    return vals

checks = []
for cell, d in [(cr*60+cc, 153) for cr, cc in [(5,5),(30,30),(55,10)]]:
    if not sea.flat[cell]: continue
    vals = pool_for_d(d, cell)
    t_manual = hazen90(np.array(vals))
    checks.append((cell, d, len(vals), t_manual, THR_sm[d-1, cell]))
for c_, d_, n_, tm, ts in checks:
    print(f"cell {c_} doy {d_}: pool {n_}, manual thr {tm:.9f}, stored smoothed thr {ts:.9f}")
# compare manual UNSMOOTHED: recompute unsmoothed for these cells
# (unsmoothed not stored; recompute quickly)
day5 = np.timedelta64(5,"D")
def unsmoothed_thr(d, cell):
    idxB = np.where(base.to_numpy() & (doyT == d))[0]
    m = np.zeros(len(Tdt), bool)
    for b in idxB:
        m |= (Tdt >= Tdt[b]-day5) & (Tdt <= Tdt[b]+day5)
    return hazen90(V[m, cell][np.isfinite(V[m, cell])])
# smoothing check: smooth31 of unsmoothed values around doy d for that cell
for c_, d_, *_ in checks:
    arr = np.array([unsmoothed_thr(x, c_) for x in range(366)])
    sm = np.array([arr[(d_-15 + o) % 366] for o in range(31)]).mean()
    print(f"cell {c_} doy {d_}: reconstructed smoothed thr {sm:.9f} vs stored {THR_sm[d_-1, c_]:.9f} diff {abs(sm-THR_sm[d_-1,c_]):.2e}")
