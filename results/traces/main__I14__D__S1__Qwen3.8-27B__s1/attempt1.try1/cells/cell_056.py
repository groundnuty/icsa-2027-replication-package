import xarray as xr, numpy as np, json

ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(ds)
m = ds['mhw'].values
print("mhw dtype:", m.dtype, "shape:", m.shape)
print("time:", ds.time.values[0], "->", ds.time.values[-1], "n =", len(ds.time))
print("lat:", ds.lat.values[0], "->", ds.lat.values[-1], "n =", len(ds.lat))
print("lon:", ds.lon.values[0], "->", ds.lon.values[-1], "n =", len(ds.lon))
print("total ones:", int(m.sum()), "(expect 4835)")
print("per-day totals on event days 2015-07-02..07:")
tt = [str(t)[:10] for t in ds.time.values]
for i in range(31, 37):
    print("  ", tt[i], int(m[i].sum()))
print("any nonzero outside 2015-07-02..07:", bool((m[:31].sum() + m[37:].sum()) > 0))
# land cells must be 0: compare with sea mask
si = np.load('/work/data/sea_idx.npy')
sea = np.zeros((60,60), bool); sea[si//60, si%60] = True
land_nonzero = (m.sum(axis=0) & ~sea).sum()
print("land cells with nonzero:", int(land_nonzero))
# every sea cell's ones must be a contiguous block within 07-02..07-07
ok = True
for c in range(m.shape[1]):
    for r in range(m.shape[0]):
        col = m[:, r, c]
        if col.any():
            idx = np.flatnonzero(col)
            if not (idx.min() >= 31 and idx.max() <= 36 and len(idx) == idx.max()-idx.min()+1):
                ok = False
print("all sea-cell MHW blocks contiguous within 07-02..07-07:", ok)
ds.close()

rep = json.load(open('output/report.json'))
print(json.dumps(rep, indent=1)[:1500])
print("fields:", sorted(rep.keys()))