import numpy as np, pandas as pd
zb = np.load("work/baseline.npz")
V = zb["sst"].reshape(len(zb["time"]), -1)
T = pd.DatetimeIndex(zb["time"].astype("datetime64[D]"))
Tdt = T.to_numpy()
doyT = np.load("work/doyT.npy"); base = np.load("work/base_mask.npy")
tc = np.load("work/thrclim.npz"); THR_sm = tc["THR"]
day5 = np.timedelta64(5,"D")

def hazen90(vals):
    v = np.sort(vals); n = len(v); h = n*0.9 - 0.5
    j = int(np.floor(h)); g = h - j
    return v[j] + (g*(v[j+1]-v[j]) if j+1 < n else 0.0)

cell = 305
unsm = np.full(366, np.nan)
for d in list(range(1,60)) + list(range(61,367)):
    idxB = np.where(base & (doyT == d))[0]
    m = np.zeros(len(Tdt), bool)
    for b in idxB:
        m |= (Tdt >= Tdt[b]-day5) & (Tdt <= Tdt[b]+day5)
    unsm[d-1] = hazen90(V[m, cell][np.isfinite(V[m, cell])])
unsm[59] = (unsm[58] + unsm[60]) / 2

d = 153
window = np.array([unsm[(d-15+o) % 366] for o in range(31)])
print("window NaNs:", int(np.isnan(window).sum()))
print("manual smooth at 153:", window.mean())
print("stored THR_sm[152,305]:", THR_sm[152, cell])
# also recompute full smooth31 on this unsm and compare elementwise
out = np.zeros(366)
for o in range(-15,16):
    out += np.roll(unsm, o, axis=0)
out /= 31
print("max abs diff full smooth31 vs stored:", np.abs(out - THR_sm[:, cell]).max())
print("where differ:", np.where(np.abs(out - THR_sm[:, cell]) > 1e-9)[0][:20])
