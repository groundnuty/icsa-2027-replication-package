import xarray as xr, numpy as np, time
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
lat = ds['latitude'].values; lon = ds['longitude'].values; t = ds['time'].values
il = (lat >= 58.69) & (lat <= 59.89)
io = (lon >= 18.69) & (lon <= 19.89)
def idx(d): return int(np.searchsorted(t, np.datetime64(d)))
b0, b1 = idx("1991-12-27"), idx("2003-01-05")
y0, y1 = idx("2017-06-01"), idx("2017-08-31")
sel = ds.sel(latitude=lat[il], longitude=lon[io])
base = sel.analysed_sst.isel(time=range(b0, b1+1)).load().values.astype('float64')
tgt  = sel.analysed_sst.isel(time=range(y0, y1+1)).load().values.astype('float64')
td = t[y0:y1+1]
np.savez_compressed('/work/region_data.npz',
    base=base, tgt=tgt,
    t_base=t[b0:b1+1].astype('datetime64[D]').astype(str),
    t_tgt=td.astype('datetime64[D]').astype(str),
    lat=lat[il], lon=lon[io])
ds.close()
print("saved", base.shape, tgt.shape)
