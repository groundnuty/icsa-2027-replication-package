import numpy as np, pickle, xarray as xr, os
base = "/data/icsa2027_data_20261101T090944Z/s1z"
meta = pickle.load(open("/tmp/target.pkl","rb"))
lat, lon = meta["lat"], meta["lon"]
slat, slon = meta["slat"], meta["slon"]
tc = pickle.load(open("/tmp/thrclim.pkl","rb"))
X = np.load("/tmp/X.npy")
Xd = X.reshape(4028, 3600)
P = pickle.load(open("/tmp/pools.pkl","rb"))
pools, dates_all = P["pools"], P["dates"]

# cell (62.96, 18.74)
il = np.flatnonzero(slat)[np.argmin(np.abs(lat[slat]-62.96))]
ik = np.flatnonzero(slon)[np.argmin(np.abs(lon[slon]-18.74))]
c = il*60 + ik
idx = pools[197]
vals = Xd[idx, c]
print("pool n:", len(idx), "finite:", int(np.isfinite(vals).sum()))
print("pool date range:", dates_all[idx[0]], dates_all[idx[-1]])
print("manual hazen90 (Jul 15 pool):", np.nanquantile(vals, 0.9, method="hazen"))
print("stored raw thr[196, c]:", tc["thr_raw"][196, c])
print("stored raw clim[196, c]:", tc["clim_raw"][196, c], "manual mean:", np.nanmean(vals))
# list the 11 window blocks
import itertools
blocks = []
prev = None; block=[idx[0]]
for i in idx[1:]:
    if i == prev+1:
        block.append(i)
    else:
        blocks.append((dates_all[block[0]], dates_all[block[-1]])); block=[i]
    prev = i
blocks.append((dates_all[block[0]], dates_all[block[-1]]))
print("n blocks:", len(blocks))
print(blocks[:3], "...", blocks[-1])
# smoothed threshold at doy 197 for this cell
print("smoothed thr[196,c]:", tc["thr_s"][196, c])
# window of days averaged for smoothing: doys 182..212 (197-15..197+15)
w = tc["thr_raw"][181:213, c]
print("manual mean of raw thr doys 182..212:", w.mean())
