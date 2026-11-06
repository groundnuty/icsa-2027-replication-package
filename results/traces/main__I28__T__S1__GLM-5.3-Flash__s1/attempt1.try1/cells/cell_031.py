import numpy as np, json, os, time
import xarray as xr
from datetime import date, timedelta

t0=time.time()
# ---------------- load staged data ----------------
data = np.load('/tmp/chunk1.npy')          # (4120,60,60) float64, dates: 1991-12-27..2003-01-05 + 2013-06-01..2013-08-31
lat = np.load('/tmp/latvals.npy')          # (60,) dataset coordinate values
lon = np.load('/tmp/lonvals.npy')          # (60,)
assert data.shape == (4120, 60, 60)

def daterange(a,b):
    out=[]; d=a
    while d<=b:
        out.append(d); d+=timedelta(days=1)
    return out

bd_ext = daterange(date(1991,12,27), date(2003,1,5))
target_dates = daterange(date(2013,6,1), date(2013,8,31))
assert len(bd_ext)==4028 and len(target_dates)==92 and len(bd_ext)+len(target_dates)==4120
NBASE = 4028

cum = [0,31,60,91,121,152,182,213,244,274,305,335]
def key(dt): return cum[dt.month-1] + dt.day
tk = np.array([key(d) for d in target_dates])
assert tk[0]==153 and tk[-1]==244

idx_of = {dt: i for i,dt in enumerate(bd_ext)}
V = data[:NBASE]                    # baseline pool-candidate values (incl. 1991-12-27..31, 2003-01-01..05)
TGT = data[NBASE:]                  # (92,60,60)
nt, nla, nlo = TGT.shape
NC = nla*nlo
T = TGT.reshape(nt, NC)

# ---------------- 1. sea cells ----------------
sea = np.isfinite(TGT).all(axis=0)
print("sea cells:", int(sea.sum()))

# ---------------- 2. climatology & threshold ----------------
thr  = np.full((366, NC), np.nan)
clim = np.full((366, NC), np.nan)
cols = np.arange(NC)
pool_sizes = set()
for d in range(1, 367):
    if d == 60: continue
    centers = [dt for dt in bd_ext if key(dt)==d and 1992<=dt.year<=2002]
    pi = []
    for s in centers:
        o = idx_of[s]
        pi.extend(range(o-5, o+6))
    pi = np.array(pi)
    assert len(centers)==11 and len(pi)==121
    pool_sizes.add(len(pi))
    P = V[pi].reshape(len(pi), NC)
    n = np.isfinite(P).sum(axis=0)
    S = np.sort(P, axis=0)
    h = n*0.9 + 0.5                                  # Hazen / Hyndman-Fan type 5
    lo = np.floor(h).astype(np.int64)
    g = h - lo
    q = (1.0-g)*S[np.clip(lo-1,0,np.maximum(n-1,0)), cols] + g*S[np.clip(lo,0,np.maximum(n-1,0)), cols]
    thr[d-1]  = np.where(n>0, q, np.nan)
    with np.errstate(invalid='ignore'):
        clim[d-1] = np.nanmean(P, axis=0)
print("pool sizes:", pool_sizes)

thr[59]  = 0.5*(thr[58] + thr[60])
clim[59] = 0.5*(clim[58] + clim[60])

def smooth31(a):
    a3 = np.tile(a, (3,1))
    c = np.zeros((a3.shape[0]+1, a.shape[1]))
    np.cumsum(a3, axis=0, out=c[1:])
    d0 = np.arange(366)
    return (c[d0+382] - c[d0+351]) / 31.0

thr_sm  = smooth31(thr)
clim_sm = smooth31(clim)
assert np.isfinite(thr_sm[tk-1]).all() and np.isfinite(clim_sm[tk-1]).all()

# ---------------- 3. per-cell MHWs ----------------
thr_d = thr_sm[tk-1]
hot = (T >= thr_d) & np.isfinite(T) & np.isfinite(thr_d)
pn = np.maximum.accumulate(np.where(~hot, np.arange(nt)[:,None], -1), axis=0)
nn = np.minimum.accumulate(np.where(~hot, np.arange(nt)[:,None], nt)[::-1], axis=0)[::-1]
cores = hot & ((nn - pn - 1) >= 5)
pc = np.maximum.accumulate(np.where(cores, np.arange(nt)[:,None], -1), axis=0)
nc_ = np.minimum.accumulate(np.where(cores, np.arange(nt)[:,None], nt)[::-1], axis=0)[::-1]
MHW2 = cores | ((~cores) & (pc >= 0) & (nc_ <= nt-1) & ((nc_ - pc - 1) <= 2))

# brute-force cross-check on sample cells
def brute(b):
    n=len(b); mhw=[False]*n
    runs=[]; i=0
    while i<n:
        if b[i]:
            j=i
            while j+1<n and b[j+1]: j+=1
            runs.append((i,j)); i=j+1
        else: i+=1
    cores=[(a,e) for a,e in runs if e-a+1>=5]
    for a,e in cores:
        for t in range(a,e+1): mhw[t]=True
    for (a1,e1),(a2,e2) in zip(cores,cores[1:]):
        if a2-e1-1 <= 2:
            for t in range(e1+1,a2): mhw[t]=True
    return mhw
rng = np.random.default_rng(7)
cells = list(rng.choice(NC, 150, replace=False)) + list(np.argsort(hot.sum(0))[-15:])
allok = all(np.array_equal(np.array(brute(hot[:,c]),dtype=bool), MHW2[:,c]) for c in cells)
print("brute-force check:", allok)
assert allok

MHW = MHW2.reshape(nt, nla, nlo).astype(np.uint8)

# ---------------- 4. regional events ----------------
active = MHW.any(axis=(1,2)).astype(bool)
events = []
i=0
while i < nt:
    if active[i]:
        j=i
        while j+1 < nt and active[j+1]: j+=1
        events.append((i,j)); i=j+1
    else:
        i+=1
ev_out = [{"onset": f"{target_dates[a]:%Y-%m-%d}", "end": f"{target_dates[b]:%Y-%m-%d}"} for a,b in events]
print("events:", ev_out)
print("active days:", int(active.sum()))

# ---------------- write outputs ----------------
os.makedirs('output', exist_ok=True)
coords = {
    "time": ("time", np.array([np.datetime64(f"{d:%Y-%m-%d}") for d in target_dates])),
    "lat":  ("lat", lat.astype('float32')),
    "lon":  ("lon", lon.astype('float32')),
}
mhw_da = xr.DataArray(MHW.astype(np.uint8), coords=coords, dims=("time","lat","lon"),
                      name="mhw", attrs={"long_name":"marine heatwave mask (per-cell MHW)",
                                         "flag_values":np.array([0,1],dtype=np.uint8),
                                         "flag_meanings":"not_in_mhw in_mhw",
                                         "units":"1"})
ds_out = xr.Dataset({"mhw": mhw_da}, coords=coords)
ds_out.to_netcdf('output/mhw_mask.nc', engine='netcdf4')
print("wrote output/mhw_mask.nc")

report = {
    "region": {"lat_min": 57.85, "lat_max": 59.05, "lon_min": 21.01, "lon_max": 22.21},
    "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
    "target_analysed": {"start": "2013-06-01", "end": "2013-08-31"},
    "events": ev_out,
    "complete": True,
    "caveats": ""
}
with open('output/report.json','w') as fh:
    json.dump(report, fh, indent=2)
print("wrote output/report.json")
print("total %.1fs" % (time.time()-t0))
