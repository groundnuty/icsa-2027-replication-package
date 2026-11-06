import numpy as np, datetime as dt, fsspec, xarray as xr

z = np.load('mhw_cache.npz', allow_pickle=False)
base_data = z['base_data']; tgt_data = z['tgt_data']
ext_days = [dt.date(1991,12,27)+dt.timedelta(days=k) for k in range(base_data.shape[0])]

# check grid + land mask consistency for a few baseline files
fs = fsspec.filesystem('onedata'); base='icsa2027_data_20261101T090944Z/s1z'
for d in [dt.date(1992,7,1), dt.date(1997,1,15), dt.date(2002,8,10), dt.date(2004,8,1)]:
    with fs.open(f"{base}/sst_{d:%Y%m%d}.nc",'rb') as f:
        ds = xr.open_dataset(f, engine='h5netcdf')
        la = ds['latitude'].values[34:94]; lo = ds['longitude'].values[213:273]
        v = ds['analysed_sst'].isel(time=0).values[34:94,213:273]
        ds.close()
    print(d, "lat[0],[-1]:", la[0], la[-1], "lon:", lo[0], lo[-1],
          "finite:", np.isfinite(v).sum(), "min/max:", np.nanmin(v), np.nanmax(v))

# pick a clearly-open-water cell (Bay of Gdansk-ish? let's use (20,20)) and (30,30)
for (i,j) in [(20,20),(30,30),(45,45)]:
    ser = base_data[:,i,j]
    fin = np.isfinite(ser)
    print(f"cell({i},{j}) baseline finite frac: {fin.mean():.3f}, min/max: {np.nanmin(ser):.2f}/{np.nanmax(ser):.2f}")
    tgt = tgt_data[:,i,j]
    print(f"   target finite frac: {np.isfinite(tgt).mean():.3f}, min/max: {np.nanmin(tgt):.2f}/{np.nanmax(tgt):.2f}")
    # August pool (doy 224 = Aug 11 window) stats vs target Aug values
    mid_aug = [k for k,d in enumerate(ext_days) if (d.month,d.day)==(8,11) and 1992<=d.year<=2002]
    pool = np.concatenate([base_data[m-5:m+6,i,j] for m in mid_aug])
    print(f"   Aug11 pool: n={pool.size} mean={np.nanmean(pool):.2f} p90={np.nanpercentile(pool,90,method='hazen'):.2f} max={np.nanmax(pool):.2f}")
    print(f"   target Aug 2-20 mean: {np.nanmean(tgt[62:81]):.2f} max: {np.nanmax(tgt):.2f}")
