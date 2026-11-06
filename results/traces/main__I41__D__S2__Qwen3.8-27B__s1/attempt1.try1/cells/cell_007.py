import numpy as np, xarray as xr
print("numpy", np.__version__)
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
times = ds['time'].values.astype('datetime64[D]')
d = np.diff(times)
print("days:", len(times), "first:", times[0], "last:", times[-1])
print("all diffs == 1 day:", bool((d == np.timedelta64(1,'D')).all()))
lat = ds['latitude'].values; lon = ds['longitude'].values
latm = (lat >= 61.57 - 1e-5) & (lat <= 62.77 + 1e-5)
lonm = (lon >= 20.17 - 1e-5) & (lon <= 21.37 + 1e-5)
print("n lat:", latm.sum(), "n lon:", lonm.sum())
print("lat range:", lat[latm][0], lat[latm][-1])
print("lon range:", lon[lonm][0], lon[lonm][-1])
ds.close()

# hazen quantile checks
a = np.arange(1, 12, dtype=float)  # 1..11
print("hazen q90 of 1..11 (expect 0.2*10+0.8*11=10.8):", np.quantile(a, 0.9, method='hazen'))
b = np.array([5.0])
print("hazen q90 of [5]:", np.nanquantile(b, 0.9, method='hazen'))
c = np.array([np.nan, 5.0, 3.0])
print("nanhazen q90 of [nan,5,3]:", np.nanquantile(c, 0.9, method='hazen'))
# manual: finite [3,5], n=2, h=(2+1)*0.9-1=1.7, j=1,g=0.7 -> 0.3*3+0.7*5=4.4
d1 = np.sort(np.array([5.0, np.nan, 3.0]))
f = np.sum(~np.isnan(d1))
h = (f+1)*0.9 - 1
j = np.floor(h).astype(int); g = h - j
Vj = d1[j]; Vj1 = d1[j+1].copy()
Vj1[np.isnan(Vj1)] = Vj[np.isnan(Vj1)]
print("manual:", (1-g)*Vj + g*Vj1)
