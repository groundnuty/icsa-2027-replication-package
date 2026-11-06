import numpy as np, xarray as xr, os
print("numpy", np.__version__)
print("xarray", xr.__version__)
try:
    import psutil
    print("mem MB:", psutil.virtual_memory().total//1024//1024)
except Exception as e:
    print("no psutil", e)

ds = xr.open_dataset('/work/sst_s2.nc', engine="h5netcdf")
t = ds['time'].values
dt = np.diff(t.astype('int64'))
print("time diffs all 1 day:", np.all(dt == 1*24*3600*10**9), "min/max:", dt.min(), dt.max())

lat = ds['latitude'].values
lon = ds['longitude'].values
eps = 1e-9
il = np.where((lat >= 61.57 - eps) & (lat <= 62.77 + eps))[0]
io = np.where((lon >= 20.17 - eps) & (lon <= 21.37 + eps))[0]
print("n lat cells:", il.size, lat[il[0]], "...", lat[il[-1]])
print("n lon cells:", io.size, lon[io[0]], "...", lon[io[-1]])
# show actual float reprs near bounds
print(repr(lat[il[0]]), repr(lat[il[-1]]), repr(lon[io[0]]), repr(lon[io[-1]]))
print("neighbors below/above bounds:", lat[il[0]-1], lat[il[-1]+1], lon[io[0]-1], lon[io[-1]+1])

# sanity of SST values (K?) at a mid-region cell in 1996 and 2009
ic, jc = il[len(il)//2], io[len(io)//2]
i96 = int((t == np.datetime64('1996-07-01'))[0])
i09 = int((t == np.datetime64('2009-07-01'))[0])
print("SST 1996-07-01 cell:", ds['analysed_sst'].isel(time=i96, latitude=ic, longitude=jc).values)
print("SST 2009-07-01 cell:", ds['analysed_sst'].isel(time=i09, latitude=ic, longitude=jc).values)
ds.close()
