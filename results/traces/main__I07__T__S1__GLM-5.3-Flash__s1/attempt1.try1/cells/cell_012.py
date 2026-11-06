import numpy as np, datetime as dt, fsspec, h5py, time
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

# coordinates from a reference file
with fs.open(f"{base}/sst_19920101.nc",'rb') as f:
    with h5py.File(f,'r') as h:
        lat = h['latitude'][:]; lon = h['longitude'][:]
print("lat[46:50]:", lat[46:50], " lat[106:110]:", lat[106:110])
print("lon[351:355]:", lon[351:355], " lon[411:415]:", lon[411:415])
ila, ila2, ilo, ilo2 = 48, 107, 353, 412
print("selected lat:", lat[ila], "...", lat[ila2], "n=", ila2-ila+1)
print("selected lon:", lon[ilo], "...", lon[ilo2], "n=", ilo2-ilo+1)
print("neighbours out of bounds:", lat[ila-1], lat[ila2+1], lon[ilo-1], lon[ilo2+1])

# spot-check time coordinate matches filename for a sample of files
z = np.load('/tmp/region_cube.npz', allow_pickle=True)
dates_str = z['dates']; cube = z['cube']
print("cube:", cube.shape, dates_str[0], dates_str[-1])
epoch = np.datetime64('1981-01-01')
idx_sample = list(range(0, len(dates_str), 157)) + [len(dates_str)-1]
mismatch = []
for i in idx_sample:
    s = str(dates_str[i])
    with fs.open(f"{base}/sst_{s}.nc",'rb') as f:
        with h5py.File(f,'r') as h:
            tv = h['time'][0]
    fdate = dt.datetime.strptime(s,'%Y%m%d').date()
    tdate = (epoch + np.timedelta64(int(tv),'s'))
    tdate = dt.datetime.utcfromtimestamp(int(tv)).date() if False else None
    d = dt.date(1981,1,1) + dt.timedelta(seconds=int(tv))
    if d != fdate: mismatch.append((s, str(d)))
print("time mismatches:", mismatch)

# sea cells within correct 60x60 region
region = cube[:, :, :60].astype(np.float64)
tgt = region[-92:]
fin_all = np.isfinite(tgt).all(axis=0)
fin_any = np.isfinite(tgt).any(axis=0)
print("cells:", region.shape[1:], "finite-all-92 (sea):", fin_all.sum(), "finite-some:", fin_any.sum(), "never finite:", (~fin_any).sum())
print("baseline finite frac:", np.isfinite(region[:-92]).mean())
