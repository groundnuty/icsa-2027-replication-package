import numpy as np, datetime as dt, pickle, fsspec, h5py
from concurrent.futures import ThreadPoolExecutor

thr = np.load('/tmp/thr.npy'); clim = np.load('/tmp/clim.npy')
base_sst = np.load('/tmp/base_sst.npy')
with open('/tmp/meta.pkl','rb') as f: meta = pickle.load(f)
base_dates = [dt.date.fromisoformat(s) for s in meta['base_dates']]
targ_sst = np.load('/tmp/targ_sst.npy')

def doy366(d):
    if d.month==2 and d.day==29: return 60
    if d.month<=2: return (d-dt.date(d.year,1,1)).days+1
    return 61+(d-dt.date(d.year,3,1)).days

# ---- 1) brute-force pool check for one cell, several days ----
i,j = 30,30
B0,B1 = dt.date(1992,1,1), dt.date(2002,12,31)
for d in [153, 200, 244]:
    vals = []
    for y in range(1992,2003):
        # find baseline dates in year y with doy == d
        # invert doy: for d<=59: Jan; d==60: Feb29; d>=61: Mar1+(d-61)
        if d <= 59: bd = dt.date(y,1,1)+dt.timedelta(days=d-1)
        elif d == 60: bd = dt.date(y,2,29)
        else: bd = dt.date(y,3,1)+dt.timedelta(days=d-61)
        for off in range(-5,6):
            X = bd+dt.timedelta(days=off)
            if B0<=X<=B1:
                k = (X - dt.date(1991,12,27)).days
                v = base_sst[k,i,j]
                if np.isfinite(v): vals.append(float(v))
    vals = np.sort(np.array(vals))
    n = vals.size; h = 0.9*n + 0.5
    lo, hi = int(np.floor(h)), int(np.ceil(h))
    p90 = vals[lo-1] + (h-lo)*(vals[hi-1]-vals[lo-1])
    t366_raw = None
    print(f"doy {d}: n={n}, manual p90={p90:.6f}, mean={vals.mean():.6f}")
# recompute raw thr/clim for that cell from pools to compare
with open('/tmp/pools.pkl','rb') as f: pools = pickle.load(f)
pool_idx = {int(k):v for k,v in pools.items()}
bs64 = base_sst.astype(np.float64)
for d in [153, 200, 244]:
    block = bs64[pool_idx[d], i, j]
    print(f"  pipeline: p90={np.nanpercentile(block,90,method='hazen'):.6f}, mean={np.nanmean(block):.6f}, n={np.isfinite(block).sum()}")

# ---- 2) target-period anomaly ----
targ_doy = np.array([doy366(dt.date.fromisoformat(s)) for s in meta['targ_dates']])
sst64 = targ_sst.astype(np.float64)
sea = np.isfinite(sst64).all(axis=0)
anom = sst64 - clim[targ_doy-1]
print("mean anomaly (K):", np.nanmean(anom[:, sea]), " min:", np.nanmin(anom[:, sea]), " max:", np.nanmax(anom[:, sea]))
hotfrac = (sst64 >= thr[targ_doy-1])[:, sea].mean()
print("hot fraction (>=):", hotfrac, " strict > :", (sst64 > thr[targ_doy-1])[:, sea].mean())

# ---- 3) control year 2005 Jun-Aug: read and compute hot fraction ----
fs = fsspec.filesystem('onedata'); basep='icsa2027_data_20261101T090944Z/s1z'
lat0,lat1,lon0,lon1 = 48,108,353,413
def read_sub(d):
    with fs.open(f"{basep}/sst_{d.strftime('%Y%m%d')}.nc",'rb') as f:
        with h5py.File(f,'r') as h:
            return h['analysed_sst'][0, lat0:lat1, lon0:lon1]
d0,d1 = dt.date(2005,6,1), dt.date(2005,8,31)
dates5 = [d0+dt.timedelta(days=k) for k in range((d1-d0).days+1)]
with ThreadPoolExecutor(16) as ex:
    sst5 = np.stack(list(ex.map(read_sub, dates5)))
s5 = sst5.astype(np.float64)
doy5 = np.array([doy366(d) for d in dates5])
sea5 = np.isfinite(s5).all(axis=0)
print("2005 sea cells == 2012 sea cells:", np.array_equal(sea5, sea))
hf5 = (s5 >= thr[doy5-1])[:, sea5].mean()
print("2005 hot fraction:", hf5, " mean anomaly:", np.nanmean((s5 - clim[doy5-1])[:, sea5]))
# also 2010 (heatwave year)
def read_range(a,b):
    d0,d1 = a,b
    dates = [d0+dt.timedelta(days=k) for k in range((d1-d0).days+1)]
    with ThreadPoolExecutor(16) as ex:
        arr = np.stack(list(ex.map(read_sub, dates)))
    return dates, arr
dates10, sst10 = read_range(dt.date(2010,6,1), dt.date(2010,8,31))
s10 = sst10.astype(np.float64); doy10 = np.array([doy366(d) for d in dates10])
sea10 = np.isfinite(s10).all(axis=0)
print("2010 hot fraction:", (s10 >= thr[doy10-1])[:, sea10].mean(), " mean anomaly:", np.nanmean((s10 - clim[doy10-1])[:, sea10]))
# clim range across year for cell (30,30)
print("clim cell(30,30): min doy:", np.argmin(clim[:,30,30])+1, np.min(clim[:,30,30]), " max doy:", np.argmax(clim[:,30,30])+1, np.max(clim[:,30,30]))
print("clim doy 15, 107, 227, 290 (cell 30,30):", clim[[15,107,227,290],30,30])
