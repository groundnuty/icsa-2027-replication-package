
import fsspec, xarray as xr, numpy as np, time, datetime

fs = fsspec.filesystem('onedata')
base = '/icsa2027_data_20261101T090944Z/s1z'

def load_range(start, end, tag):
    dates = []
    d = start
    while d <= end:
        dates.append(d); d += datetime.timedelta(days=1)
    rows = []
    t0 = time.time()
    for i, d in enumerate(dates):
        name = 'sst_' + d.strftime('%Y%m%d') + '.nc'
        with fs.open(base + '/' + name, "rb") as f:
            ds = xr.open_dataset(f, engine="h5netcdf")
            v = ds['analysed_sst'].isel(latitude=slice(66,126), longitude=slice(531,591)).values[0]
            ds.close()
        rows.append(v.astype(np.float64))
        if (i+1) % 400 == 0:
            print(f"  {i+1}/{len(dates)} loaded, elapsed {time.time()-t0:.0f}s", flush=True)
    arr = np.stack(rows)
    np.save(f'work/part_{tag}.npy', arr)
    print(tag, "shape:", arr.shape, "total time:", round(time.time()-t0,1), "s")

load_range(datetime.date(1997,1,1), datetime.date(2002,12,31), 'b2')
load_range(datetime.date(2003,1,1), datetime.date(2003,1,5), 'b3')
load_range(datetime.date(2007,6,1), datetime.date(2007,8,31), 't1')
