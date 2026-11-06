import numpy as np, xarray as xr, datetime

thr = np.load('/work/thr.npy'); clim = np.load('/work/clim.npy')
lat_idx = np.load('/work/lat_idx.npy'); lon_idx = np.load('/work/lon_idx.npy')
Nlat = len(lat_idx)

def flat(r, c): return r * Nlat + c

# independent recomputation for doy=166 (Jun 15), cell (10,10)
r, c = 10, 10
cell = flat(r, c)
pools = []
for y in range(1992, 2003):
    b = datetime.date(y, 6, 15)
    for k in range(-5, 6):
        dt = b + datetime.timedelta(days=k)
        ds = xr.open_dataset(f'/work/data/sst_{dt.strftime("%Y%m%d")}.nc', engine='h5netcdf')
        pools.append(float(ds['analysed_sst'].values[0][lat_idx[r], lon_idx[c]]))
        ds.close()
pools = np.array(pools)
q90 = np.nanquantile(pools, 0.9, method="hazen")
print("pool:", len(pools), "nan:", np.isnan(pools).sum())
print("thr[165]: indep", q90, "saved", thr[165, cell], "equal:", np.isclose(q90, thr[165, cell]))
print("clim[165]: indep", np.nanmean(pools), "saved", clim[165, cell], "equal:", np.isclose(np.nanmean(pools), clim[165, cell]))

# doy=61 (Mar 1), cell (30,40)
r2, c2 = 30, 40
cell2 = flat(r2, c2)
pools61 = []
for y in range(1992, 2003):
    b = datetime.date(y, 3, 1)
    for k in range(-5, 6):
        dt = b + datetime.timedelta(days=k)
        ds = xr.open_dataset(f'/work/data/sst_{dt.strftime("%Y%m%d")}.nc', engine='h5netcdf')
        pools61.append(float(ds['analysed_sst'].values[0][lat_idx[r2], lon_idx[c2]]))
        ds.close()
pools61 = np.array(pools61)
q61 = np.nanquantile(pools61, 0.9, method="hazen")
print("thr[60]: indep", q61, "saved", thr[60, cell2], "equal:", np.isclose(q61, thr[60, cell2]))
ds = xr.open_dataset('/work/data/sst_19920229.nc', engine='h5netcdf')
v29 = ds['analysed_sst'].values[0][lat_idx[r2], lon_idx[c2]]
ds.close()
print("1992-02-29 in doy61 pool:", v29 in pools61)
# doy=59 (Feb 28): window Feb 23..Mar 5 also contains Feb 29
print("1992-02-29 in doy59 window (Feb23..Mar5):", datetime.date(1992,2,23) <= datetime.date(1992,2,29) <= datetime.date(1992,3,5))
