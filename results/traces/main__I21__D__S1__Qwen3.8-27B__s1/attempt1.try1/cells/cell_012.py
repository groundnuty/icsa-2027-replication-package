import xarray as xr, numpy as np, glob, re, datetime, time

t0 = time.time()
files = sorted(glob.glob('/work/data/sst_*.nc'))

def daterange(d0, d1):
    d = d0
    while d <= d1:
        yield d
        d += datetime.timedelta(days=1)

base_dates = list(daterange(datetime.date(1991,12,27), datetime.date(2003,1,5)))
tgt_dates  = list(daterange(datetime.date(2021,6,1), datetime.date(2021,8,31)))
name2date = {}
for d in base_dates + tgt_dates:
    name2date[f'sst_{d.strftime("%Y%m%d")}.nc'] = d

ds0 = xr.open_dataset(files[0], engine='h5netcdf')
lat = ds0.latitude.values; lon = ds0.longitude.values
ilats = np.where((lat >= 57.33) & (lat <= 58.53))[0]
ilons = np.where((lon >= 9.03) & (lon <= 10.23))[0]
lat_sub = lat[ilats].astype(np.float64); lon_sub = lon[ilons].astype(np.float64)
print("region shape:", lat_sub.shape, lon_sub.shape, "lat range:", lat_sub.min(), lat_sub.max(), "lon range:", lon_sub.min(), lon_sub.max())
ds0.close()

def load_range(dates, files):
    arr = np.empty((len(dates), len(ilats), len(ilons)), dtype=np.float64)
    fset = {re.search(r'sst_(\d{8})', f).group(1): f for f in files}
    for i, d in enumerate(dates):
        f = fset[d.strftime('%Y%m%d')]
        ds = xr.open_dataset(f, engine='h5netcdf')
        v = ds.analysed_sst.values[0, ilats[:,None], ilons[None,:]]
        assert ds.analysed_sst.time.values[0] == np.datetime64(d), d
        arr[i] = v.astype(np.float64)
        ds.close()
    return arr

base_arr = load_range(base_dates, files)
tgt_arr  = load_range(tgt_dates, files)
print("base:", base_arr.shape, "tgt:", tgt_arr.shape, "in", round(time.time()-t0,1), "s")
np.savez_compressed('/work/region.npz',
                    base_dates=np.array([d.strftime('%Y-%m-%d') for d in base_dates]),
                    tgt_dates=np.array([d.strftime('%Y-%m-%d') for d in tgt_dates]),
                    lat=lat_sub, lon=lon_sub,
                    base_sst=base_arr, tgt_sst=tgt_arr)
print("saved /work/region.npz")
print("base finite frac:", np.isfinite(base_arr).mean(), "tgt finite frac:", np.isfinite(tgt_arr).mean())
sea = np.isfinite(tgt_arr).all(axis=0)
print("sea cells (finite every target day):", sea.sum(), "of", sea.size)
