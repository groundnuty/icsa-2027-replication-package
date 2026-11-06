import numpy as np, pandas as pd
zb = np.load("work/baseline.npz")
V = zb["sst"].reshape(len(zb["time"]), -1)
T = pd.DatetimeIndex(zb["time"].astype("datetime64[D]"))
Tdt = T.to_numpy()
doyT_file = np.load("work/doyT.npy")
base_file = np.load("work/base_mask.npy")

def doy_of(dt):
    m, d = dt.month, dt.day
    if m <= 2:
        return (dt - pd.Timestamp(dt.year, 1, 1)).days + 1
    return (pd.Timestamp(2004, m, d) - pd.Timestamp(2004, 1, 1)).days + 1
doyT_new = np.array([doy_of(x) for x in T])
base_new = np.asarray(((T >= pd.Timestamp("1992-01-01")) & (T <= pd.Timestamp("2002-12-31"))))
print("doy arrays equal:", np.array_equal(doyT_file, doyT_new), "| base equal:", np.array_equal(base_file, base_new))

cell = 305
day5 = np.timedelta64(5,"D")
def hazen90(vals):
    v = np.sort(vals); n = len(v); h = n*0.9 - 0.5
    j = int(np.floor(h)); g = h - j
    return v[j] + (g*(v[j+1]-v[j]) if j+1 < n else 0.0)

def via_file(d):
    idxB = np.where(base_file & (doyT_file == d))[0]
    m = np.zeros(len(Tdt), bool)
    for b in idxB:
        m |= (Tdt >= Tdt[b]-day5) & (Tdt <= Tdt[b]+day5)
    vv = V[m, cell]
    return hazen90(vv[np.isfinite(vv)]), m.sum()

diffs = []
for d in list(range(1,60)) + list(range(61,367)):
    t1, n1 = via_file(d)
    # reconstruction style
    vals = []
    for b in T[base_new]:
        if doy_of(b) != d: continue
        m = (Tdt >= (b - pd.Timedelta(days=5)).to_numpy()) & (Tdt <= (b + pd.Timedelta(days=5)).to_numpy())
        vals.extend(V[m, cell][np.isfinite(V[m, cell])].tolist())
    t2 = hazen90(np.array(vals))
    if not np.isclose(t1, t2, rtol=1e-12, atol=1e-9):
        diffs.append((d, t1, t2, n1, len(vals)))
print("num differing doys:", len(diffs))
for d in diffs[:10]:
    print(d)
