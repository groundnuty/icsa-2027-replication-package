import numpy as np, pandas as pd, time
t0=time.time()
zb = np.load("work/baseline.npz")
V = zb["sst"]; T = pd.DatetimeIndex(zb["time"].astype("datetime64[D]"))
Tdt = T.to_numpy()
doyT = np.load("work/doyT.npy"); base = np.load("work/base_mask.npy")
ncells = V.shape[1]
day5 = np.timedelta64(5,"D")

# verify hazen vs manual HF type 5
rng = np.random.default_rng(0)
x = rng.normal(280, 3, 10)
def hazen_manual(a, p=0.9):
    a = np.sort(a); n = len(a); h = n*p + 0.5 - 1  # 0-based position
    j = int(np.floor(h)); g = h - j
    return a[j] + (g*(a[j+1]-a[j]) if j+1 < n else 0.0)
xs = [rng.normal(280,3,7).tolist() for _ in range(20)]
ok = all(abs(np.nanpercentile(v, 90, method="hazen") - hazen_manual(v)) < 1e-12 for v in xs)
print("hazen matches manual HF type5:", ok)
print("nans in V:", int(np.isnan(V).sum()), "of", V.size)

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
print("pool sizes min/max:", min(sizes), max(sizes), "time", round(time.time()-t0,1),"s")
print("NaNs THR pre-smooth:", int(np.isnan(THR).sum()), "CLIM:", int(np.isnan(CLIM).sum()))

def smooth31(a):
    out = np.zeros_like(a)
    for o in range(-15, 16):
        out += np.roll(a, o, axis=0)
    return out / 31.0

THRs = smooth31(THR); CLIMs = smooth31(CLIM)
print("NaNs THR smooth:", int(np.isnan(THRs).sum()), "CLIM smooth:", int(np.isnan(CLIMs).sum()))
np.savez("work/thrclim.npz", THR=THRs, CLIM=CLIMs)
# sanity: show smoothed threshold for June-Aug doys at a central cell
zt = np.load("work/target.npz"); sea = zt["sea"]
c = int(np.argmax(sea.sum(axis=0)) * 60 + np.argmax(sea.sum(axis=1)))
cc = c % 60; cr = c // 60
doyT2021 = np.array([(pd.Timestamp(2004, m, dd) - pd.Timestamp(2004,1,1)).days + 1 for m,dd in [(6,1),(6,21),(7,15),(8,31)]])
print("sample cell", cr, cc, "thr Jun1/Jul15/Aug31:", THRs[doyT2021[0], cr*60+cc], THRs[doyT2021[2], cr*60+cc], THRs[doyT2021[3], cr*60+cc])
print("saved work/thrclim.npz", round(time.time()-t0,1),"s total")
