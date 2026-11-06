import numpy as np, xarray as xr, datetime

thr = np.load('/work/thr.npy'); clim = np.load('/work/clim.npy')
thr_raw = np.load('/work/thr_raw.npy'); clim_raw = np.load('/work/clim_raw.npy')
sea = np.load('/work/sea_mask.npy')
lat_idx = np.load('/work/lat_idx.npy'); lon_idx = np.load('/work/lon_idx.npy')
Nlat = len(lat_idx)
def flat(r,c): return r*Nlat + c

def smooth31(arr):
    out = np.zeros_like(arr)
    for k in range(-15, 16):
        out += np.roll(arr, k, axis=0)
    return out / 31.0

thr_chk = smooth31(thr_raw); clim_chk = smooth31(clim_raw)
print("allclose incl NaN-equal:", np.allclose(thr, thr_chk, equal_nan=True), np.allclose(clim, clim_chk, equal_nan=True))
diff = ~np.isclose(thr, thr_chk, equal_nan=True)
print("n differing (thr):", int(diff.sum()), " all on land cells:", bool((diff & sea[None,:]).sum() == 0))
print("raw thr NaN columns all land:", bool(np.isnan(thr_raw).any(axis=0)[~sea].sum() == 314) and bool(np.isnan(thr_raw).any(axis=0)[sea].sum() == 0))
print("raw[59]==mean(58,60) on sea cells:", bool(np.allclose(thr_raw[59, sea], 0.5*(thr_raw[58, sea]+thr_raw[60, sea]))))

# Now redo the independent pool check with CORRECT canonical date: doy 166 = Jun 14
b_dnum = 166
mdd = (datetime.date(2001,3,1) + datetime.timedelta(days=b_dnum-61)).strftime('%b %d')
print("canonical date of doy 166:", mdd)
r, c = 10, 10
cell = flat(r, c)
pools = []
for y in range(1992, 2003):
    b = datetime.date(y, 6, 14)
    for k in range(-5, 6):
        dt = b + datetime.timedelta(days=k)
        ds = xr.open_dataset(f'/work/data/sst_{dt.strftime("%Y%m%d")}.nc', engine='h5netcdf')
        pools.append(float(ds['analysed_sst'].values[0][lat_idx[r], lon_idx[c]]))
        ds.close()
pools = np.array(pools)
q90 = np.nanquantile(pools, 0.9, method="hazen")
mn = np.nanmean(pools)
print("RAW thr[165] indep:", q90, " pipeline:", thr_raw[165, cell], " equal:", np.isclose(q90, thr_raw[165, cell]))
print("RAW clim[165] indep:", mn, " pipeline:", clim_raw[165, cell], " equal:", np.isclose(mn, clim_raw[165, cell]))

# cross-check pipeline pool values == independent file reads for this (doy, cell)
ext = np.load('/work/ext.npy')
ext_dates = []
d = datetime.date(1991,12,27)
while d <= datetime.date(2003,1,5):
    ext_dates.append(d); d += datetime.timedelta(days=1)
d2i = {dt: i for i, dt in enumerate(ext_dates)}
idxs = []
for y in range(1992, 2003):
    i0 = d2i[datetime.date(y, 6, 14)]
    idxs.extend(range(i0-5, i0+6))
pp = ext[np.asarray(idxs)][:, cell]
print("pool multisets identical:", bool(np.array_equal(np.sort(pp[~np.isnan(pp)]), np.sort(pools[~np.isnan(pools)]))))

# 2016-06-15 target day uses which doy?
print("2016-06-15 tm_yday:", datetime.date(2016,6,15).timetuple().tm_yday)
print("2016-06-01 tm_yday:", datetime.date(2016,6,1).timetuple().tm_yday, " 2016-08-31:", datetime.date(2016,8,31).timetuple().tm_yday)
