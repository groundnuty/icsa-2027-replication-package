import xarray as xr, numpy as np, time, datetime as dt
import warnings; warnings.filterwarnings('ignore')

# benchmark 50 file loads
t_start = time.time()
lati = slice(34, 94)   # 54.18..55.36
loji = slice(213, 273) # 13.26..14.44
for d in [dt.date(1992,3,1)+dt.timedelta(days=i) for i in range(50)]:
    ds = xr.open_dataset(f'/work/data/sst_{d.strftime("%Y%m%d")}.nc', engine='h5netcdf')
    v = ds['analysed_sst'].values[0, lati, loji]
    ds.close()
el = time.time()-t_start
print(f"50 loads: {el:.1f}s -> {50/el*60:.0f}/min, total est {el/50*4120/60:.1f} min")
print("sample dtype:", v.dtype, "shape:", v.shape)

# verify coordinates stable across a spread of files
for d in [dt.date(1991,12,27), dt.date(2000,6,15), dt.date(2004,8,31)]:
    ds = xr.open_dataset(f'/work/data/sst_{d.strftime("%Y%m%d")}.nc', engine='h5netcdf')
    print(d, "time:", ds['time'].values, "lat0/last:", ds['latitude'].values[0], ds['latitude'].values[-1],
          "lon0/last:", ds['longitude'].values[0], ds['longitude'].values[-1],
          "latsz/lon sz:", ds['latitude'].size, ds['longitude'].size)
    ds.close()
