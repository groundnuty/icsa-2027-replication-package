import fsspec, xarray as xr, numpy as np, datetime as dt, json, os, time

interm = np.load('/tmp/mhw_interm.npz')
thr_sm = interm['thr_sm']  # (366, 60, 60) float64
clim_sm = interm['clim_sm']

fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
sst = ds['analysed_sst']
tvals = ds.time.values
lat = ds.latitude.values; lon = ds.longitude.values
latmask = (lat >= 54.13) & (lat <= 55.33); lonmask = (lon >= 14.67) & (lon <= 15.87)
la = np.where(latmask)[0]; lo = np.where(lonmask)[0]
lat_sl = slice(la[0], la[-1]+1); lon_sl = slice(lo[0], lo[-1]+1)

t0i = np.searchsorted(tvals, np.datetime64('2008-06-01'))
t1i = np.searchsorted(tvals, np.datetime64('2008-08-31'), 'right')
tdates = tvals[t0i:t1i].astype('datetime64[D]')
ndays = len(tdates)
print("target days:", ndays, tdates[0], "->", tdates[-1])

t0 = time.time()
sst_t = sst.isel(time=slice(t0i,t1i), latitude=lat_sl, longitude=lon_sl).values.astype(np.float64)
print("target read %.1fs shape %s" % (time.time()-t0, sst_t.shape))

# sea cells: finite SST on every day of the target period
sea = np.isfinite(sst_t).all(axis=0)
print("sea cells:", int(sea.sum()))

# day-of-year mapping by month/day (leap-safe, 1..366)
def doy_of(date64):
    d = dt.date.fromisoformat(str(date64))
    if d.month == 2 and d.day == 29: return 60
    return (d - dt.date(d.year,1,1)).days + 1
doy_idx = np.array([doy_of(d) - 1 for d in tdates])   # 0-based into 366
print("doy_idx first/last:", doy_idx[:3].tolist(), doy_idx[-3:].tolist())

# hot: SST >= threshold for that doy (in kelvin as stored)
thr_t = thr_sm[doy_idx]          # (92, 60, 60)
hot = (sst_t >= thr_t)
hot &= sea[None, :, :]
print("hot day-cell count:", int(hot.sum()), " hot fraction of sea cells:", hot.sum()/sea.sum()/ndays)

# per-cell MHW: runs of >=5 consecutive hot days, gaps of 1-2 non-hot days joined
nT, nY, nX = hot.shape
mhw = np.zeros_like(hot, dtype=bool)
runs5 = 0; joined = 0; final_runs = 0
for yy in range(nY):
    for xx in range(nX):
        h = hot[:, yy, xx]
        if not h.any(): continue
        # initial runs >= 5
        d = np.diff(h.astype(np.int8))
        starts = np.where(d == 1)[0] + 1
        ends = np.where(d == -1)[0] + 1
        if h[0]: starts = np.r_[0, starts]
        if h[-1]: ends = np.r_[ends, nT]
        lens = ends - starts
        keep = lens >= 5
        runs5 += int(keep.sum())
        rs = starts[keep]; re = ends[keep]
        if len(rs) == 0: continue
        # join runs separated by 1-2 non-hot days
        ms = [rs[0]]; me = [re[0]]
        for s, e in zip(rs[1:], re[1:]):
            gap = s - me[-1]      # non-hot days between
            if 1 <= gap <= 2:
                joined += 1
                me[-1] = e
            else:
                ms.append(s); me.append(e)
        final_runs += len(ms)
        for s, e in zip(ms, me):
            mhw[s:e, yy, xx] = True

print("initial runs>=5:", runs5, " gaps joined:", joined, " final per-cell MHWs:", final_runs)
print("mhw day-cell count:", int(mhw.sum()))

# regional: active day = at least one sea cell inside a per-cell MHW
active = mhw.any(axis=(1,2))
print("active days:", int(active.sum()), "/", ndays)
vals, cnts = np.unique(active, return_counts=True)
print(dict(zip(vals.tolist(), cnts.tolist())))
ar = active.astype(np.int8); dd = np.diff(ar)
ev_starts = np.where(dd == 1)[0] + 1
ev_ends = np.where(dd == -1)[0]
if active[0]: ev_starts = np.r_[0, ev_starts]
if active[-1]: ev_ends = np.r_[ev_ends, ndays-1]
events = [(str(tdates[s]), str(tdates[e])) for s, e in zip(ev_starts, ev_ends)]
print("regional events:", events)
print("event lengths:", [int((np.datetime64(e)-np.datetime64(s)).astype(int))+1 for s,e in events])

np.savez_compressed('/tmp/mhw_mask.npz', mhw=mhw.astype(np.uint8))
print("saved mask")
