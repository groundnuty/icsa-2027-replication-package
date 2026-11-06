import fsspec, xarray as xr, numpy as np, datetime as dt, json, os, time

ver = np.load('/tmp/verify_thr.npz')
thr_sm = ver['thr_sm2']; clim_sm = ver['clim_sm2']   # independent path

fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
sst = ds['analysed_sst']; tvals = ds.time.values
lat = ds.latitude.values; lon = ds.longitude.values
la = np.where((lat>=54.13)&(lat<=55.33))[0]; lo = np.where((lon>=14.67)&(lon<=15.87))[0]
t0i = int(np.searchsorted(tvals, np.datetime64('2008-06-01')))
t1i = int(np.searchsorted(tvals, np.datetime64('2008-08-31'), 'right'))
tdates = tvals[t0i:t1i].astype('datetime64[D]'); nT = len(tdates)

sst_t = sst.isel(time=slice(t0i,t1i), latitude=slice(la[0],la[-1]+1), longitude=slice(lo[0],lo[-1]+1)).values.astype(np.float64)
sea = np.isfinite(sst_t).all(axis=0)

def doy_of(date64):
    d = dt.date.fromisoformat(str(date64))
    if d.month==2 and d.day==29: return 60
    return (d - dt.date(d.year,1,1)).days + 1
doy_idx = np.array([doy_of(d)-1 for d in tdates])
hot = (sst_t >= thr_sm[doy_idx]) & sea[None,:,:]

# brute-force per-cell MHW: scan runs and merge with lookahead of up to 2 non-hot days
def runs_of(h):
    out=[]; s=None
    for i,v in enumerate(h):
        if v and s is None: s=i
        if (not v or i==len(h)-1) and s is not None:
            e = i if not v else i+1
            out.append((s,e)); s=None
    return out

nY,nX = hot.shape[1], hot.shape[2]
mhw2 = np.zeros_like(hot)
nruns=0; nmerged=0
for yy in range(nY):
    for xx in range(nX):
        h = hot[:,yy,xx]
        if not h.any(): continue
        rs = runs_of(h)
        keep = [(s,e) for s,e in rs if e-s >= 5]
        nruns += len(keep)
        if not keep: continue
        merged=[keep[0]]
        for s,e in keep[1:]:
            if s - merged[-1][1] <= 2:
                merged[-1] = (merged[-1][0], e); nmerged += 1
            else:
                merged.append((s,e))
        for s,e in merged: mhw2[s:e, yy, xx] = True

old = np.load('/tmp/mhw_mask.npz')['mhw'].astype(bool)
print("mhw masks identical:", np.array_equal(mhw2, old))
print("day-cells:", int(mhw2.sum()), " runs:", nruns, " merged:", nmerged)

active = mhw2.any(axis=(1,2))
ev = []
s = None
for i,v in enumerate(active):
    if v and s is None: s=i
    if (not v or i==nT-1) and s is not None:
        e = i if not v else i+1
        ev.append((str(tdates[s]), str(tdates[e-1]))); s=None
print("events (independent):", ev)

# sanity: first day active must have >=1 cell in MHW (target starts hot?); check hot on day 0 region-wide
print("day0 hot cells:", int(hot[0].sum()), " mhw cells day0:", int(mhw2[0].sum()))
np.savez_compressed('/tmp/mhw_mask2.npz', mhw=mhw2.astype(np.uint8))
print("ok")
