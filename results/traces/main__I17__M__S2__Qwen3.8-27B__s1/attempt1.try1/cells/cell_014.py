
import numpy as np, xarray as xr, datetime as dtm
sea2 = np.load("/tmp/sea2.npy"); thrS = np.load("/tmp/thrS.npy")
ds = xr.open_dataset("/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc", engine="h5netcdf")
t = ds.time.values
si = np.argwhere(sea2); n_sea = si.shape[0]
reg = ds.analysed_sst.isel(latitude=(ds.latitude>=56.63)&(ds.latitude<=57.83),
                           longitude=(ds.longitude>=20.23)&(ds.longitude<=21.43))
bas = reg.isel(time=slice(3647, 7675)).values.astype("float64")
Xb = bas[:, si[:,0], si[:,1]]

mlen = [31,29,31,30,31,30,31,31,30,31,30,31]
mdoy = np.zeros((12,31), int)
off=0
for m in range(12):
    mdoy[m,:mlen[m]] = off+1+np.arange(mlen[m]); off += mlen[m]
doy2md = {}
for m in range(12):
    for dd in range(1, mlen[m]+1):
        doy2md[mdoy[m, dd-1]] = (m+1, dd)

t_bas = t[3647:7675]
d2idx = {np.datetime64(d): i for i, d in enumerate(t_bas)}
years = list(range(1992,2003))

def pool_vals(c, d):
    mo, day = doy2md[d]
    vals = []
    for y in years:
        b = dtm.date(y, mo, day)
        for k in range(-5, 6):
            x = b + dtm.timedelta(days=k)
            vals.append(Xb[d2idx[np.datetime64(x)], c])
    return np.array(vals)

def hazen_manual(vals):
    v = np.sort(vals); n = len(v); h = n*0.9 + 0.5
    lo = int(np.floor(h)); frac = h - lo
    return float(v[-1] if lo >= n else v[lo-1] + frac*(v[lo]-v[lo-1]))

maxd = 0.0
for c in [0, 777, 1234, 2500, 3303]:
    # full per-day thresholds for this cell, manually
    per = {}
    for d in range(1, 367):
        if d == 60:
            continue
        per[d] = hazen_manual(pool_vals(c, d))
    per[60] = 0.5*(per[59] + per[61])
    for d in range(1, 367):
        sm = np.mean([per[((d-16+366*15) % 366) + 1] if False else per[(d-15+i-1) % 366 + 1] for i in range(31)])
        # window days d-15 .. d+15 (1-based), modulo 366 with 1..366 wrap
        sm = np.mean([per[(((d - 15 + i) - 1) % 366) + 1] for i in range(31)])
        diff = abs(sm - thrS[c, d-1])
        maxd = max(maxd, diff)
    print(f"cell {c}: max |manual-pipeline| over all 366 doys = {maxd:.3e}")
print("GLOBAL MAX DIFF:", maxd)

# check wrap specifically at doy 1 and 366 for one cell (visual)
c = 0
per = {}
for d in [352,353,354,355,356,357,358,359,360,361,362,363,364,365,366,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16]:
    if d == 60: continue
    per[d] = hazen_manual(pool_vals(c, d))
per[60] = 0.5*(per[59]+per[61])
sm1 = np.mean([per[(((1 - 15 + i) - 1) % 366) + 1] for i in range(31)])
sm366 = np.mean([per[(((366 - 15 + i) - 1) % 366) + 1] for i in range(31)])
print("wrap check cell 0: doy1 manual %.6f pipeline %.6f | doy366 manual %.6f pipeline %.6f" %
      (sm1, thrS[c,0], sm366, thrS[c,365]))
