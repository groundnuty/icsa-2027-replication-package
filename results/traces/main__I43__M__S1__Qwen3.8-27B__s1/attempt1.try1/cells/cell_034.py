import numpy as np, pickle
meta = pickle.load(open("/tmp/target.pkl","rb"))
lat, lon = meta["lat"], meta["lon"]
slat, slon = meta["slat"], meta["slon"]
tc = pickle.load(open("/tmp/thrclim.pkl","rb"))
X = np.load("/tmp/X.npy")
Xd = X.reshape(4028, 3600)
P = pickle.load(open("/tmp/pools.pkl","rb"))
pools, dates_all = P["pools"], P["dates"]

il = int(np.argmin(np.abs(lat[slat]-62.96)))
ik = int(np.argmin(np.abs(lon[slon]-18.74)))
print("subgrid lat/lon:", lat[slat][il], lon[slon][ik])
c = il*60 + ik
idx = pools[197]
vals = Xd[idx, c]
print("pool n:", len(idx), "finite:", int(np.isfinite(vals).sum()))
print("pool date range:", dates_all[idx[0]], dates_all[idx[-1]])
print("manual hazen90 (Jul 15 pool):", np.nanquantile(vals, 0.9, method="hazen"))
print("stored raw thr[196, c]:", tc["thr_raw"][196, c])
print("stored raw clim[196, c]:", tc["clim_raw"][196, c], "manual mean:", np.nanmean(vals))
blocks = []
prev = None; block=[idx[0]]
for i in idx[1:]:
    if i == prev+1:
        block.append(i)
    else:
        blocks.append((dates_all[block[0]].isoformat(), dates_all[block[-1]].isoformat())); block=[i]
    prev = i
blocks.append((dates_all[block[0]].isoformat(), dates_all[block[-1]].isoformat()))
print("n blocks:", len(blocks)); print("first 3:", blocks[:3], "last:", blocks[-1])
print("smoothed thr[196,c]:", tc["thr_s"][196, c], "| manual mean of raw thr doys 182..212:", tc["thr_raw"][181:213, c].mean())
