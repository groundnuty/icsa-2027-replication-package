import numpy as np, pandas as pd, time
t0=time.time()
zb = np.load("work/baseline.npz")
V = zb["sst"].reshape(len(zb["time"]), -1)  # (4028, 3600)
T = pd.DatetimeIndex(zb["time"].astype("datetime64[D]"))
Tdt = T.to_numpy()
doyT = np.load("work/doyT.npy"); base = np.load("work/base_mask.npy")
ncells = V.shape[1]
day5 = np.timedelta64(5,"D")

THR = np.full((366, ncells), np.nan)
CLIM = np.full((366, ncells), np.nan)
sizes = []
for d in list(range(1, 60)) + list(range(61, 367)):
    idxB = np.where(base & (doyT == d))[0]
    mask = np.zeros(len(Tdt), bool)
    for b in idxB:
        mask |= (Tdt >= Tdt[b]-day5) & (Tdt <= Tdt[b]+day5)
    P = V[mask]
    sizes.append(P.shape[0])
    CLIM[d] = np.nanmean(P, axis=0)
    THR[d] = np.nanpercentile(P, 90.0, axis=0, method="hazen")
THR[60] = (THR[59]+THR[61])/2.0
CLIM[60] = (CLIM[59]+CLIM[61])/2.0
print("pool sizes min/max:", min(sizes), max(sizes))
print("NaNs THR pre-smooth:", int(np.isnan(THR).sum()), "CLIM:", int(np.isnan(CLIM).sum()))

def smooth31(a):
    out = np.zeros_like(a)
    for o in range(-15, 16):
        out += np.roll(a, o, axis=0)
    return out / 31.0

THRs = smooth31(THR); CLIMs = smooth31(CLIM)
print("NaNs THR smooth:", int(np.isnan(THRs).sum()), "CLIM smooth:", int(np.isnan(CLIMs).sum()))
np.savez("work/thrclim.npz", THR=THRs, CLIM=CLIMs)
zt = np.load("work/target.npz"); sea = zt["sea"]
cr, cc = 30, 30
for m,dd in [(6,1),(7,15),(8,31)]:
    d = (pd.Timestamp(2004,m,dd) - pd.Timestamp(2004,1,1)).days + 1
    print("doy", d, "cell(30,30) smoothed thr:", THRs[d, cr*60+cc], "clim:", CLIMs[d, cr*60+cc])
print("time", round(time.time()-t0,1),"s")
