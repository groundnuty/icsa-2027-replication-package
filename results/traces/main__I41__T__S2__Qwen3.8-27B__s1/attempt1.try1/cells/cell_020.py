import numpy as np, pandas as pd
zb = np.load("work/baseline.npz")
V = zb["sst"].reshape(len(zb["time"]), -1)
T = pd.DatetimeIndex(zb["time"].astype("datetime64[D]"))
Tdt = T.to_numpy()
tc = np.load("work/thrclim.npz"); THR_sm = tc["THR"]

def doy_of(dt):
    m, d = dt.month, dt.day
    if m <= 2:
        return (dt - pd.Timestamp(dt.year, 1, 1)).days + 1
    return (pd.Timestamp(2004, m, d) - pd.Timestamp(2004, 1, 1)).days + 1
doyT = np.array([doy_of(x) for x in T])
base = ((T >= pd.Timestamp("1992-01-01")) & (T <= pd.Timestamp("2002-12-31"))).to_numpy()
day5 = np.timedelta64(5,"D")

def hazen90(vals):
    v = np.sort(vals); n = len(v); h = n*0.9 - 0.5
    j = int(np.floor(h)); g = h - j
    return v[j] + (g*(v[j+1]-v[j]) if j+1 < n else 0.0)

def unsmoothed_thr(d, cell):
    idxB = np.where(base & (doyT == d))[0]
    m = np.zeros(len(Tdt), bool)
    for b in idxB:
        m |= (Tdt >= Tdt[b]-day5) & (Tdt <= Tdt[b]+day5)
    return hazen90(V[m, cell][np.isfinite(V[m, cell])])

worst = 0.0
for c_, d_ in [(305,153),(1830,153),(3310,153),(1830,60),(1830,244)]:
    arr = np.array([unsmoothed_thr(x, c_) for x in range(366)])
    # day 60 unsmoothed = mean(59,61)
    arr[59] = (arr[58]+arr[60])/2
    sm = np.array([arr[(d_ - 15 + o) % 366] for o in range(31)]).mean()
    diff = abs(sm - THR_sm[d_-1, c_])
    worst = max(worst, diff)
    print(f"cell {c_} doy {d_}: reconstructed {sm:.10f} vs stored {THR_sm[d_-1, c_]:.10f} diff {diff:.3e}")
print("worst diff:", worst)
