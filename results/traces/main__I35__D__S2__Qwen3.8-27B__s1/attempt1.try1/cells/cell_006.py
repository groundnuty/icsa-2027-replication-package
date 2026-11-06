import xarray as xr, numpy as np
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
lat = ds['latitude'].values; lon = ds['longitude'].values
eps = 1e-4
lat_sel = (lat >= 59.93 - eps) & (lat <= 61.13 + eps)
lon_sel = (lon >= 18.69 - eps) & (lon <= 19.89 + eps)
print('n lat cells:', lat_sel.sum(), 'n lon cells:', lon_sel.sum())
print('lat range:', lat[lat_sel][0], '->', lat[lat_sel][-1])
print('lon range:', lon[lon_sel][0], '->', lon[lon_sel][-1])
print('excluded neighbours:', lat[np.r_[lat_sel.argmax()-1:]][-1], lat[np.nonzero(~lat_sel)[0][0]], lon[np.nonzero(~lon_sel)[0][0]], lon[np.nonzero(~lon_sel)[0][-1]])

# hazen quantile sanity check vs Hyndman-Fan type 5 formula
x = np.arange(1, 11, dtype=float)
def hazen(x, q):
    n = len(x); x = np.sort(x)
    # h_i = (i-0.5)/n ; find i such that h_{i-1} <= p <= h_i
    i = np.clip(np.ceil(q*n + 0.5), 1, n)  # solve p <= (i-0.5)/n -> i >= p*n+0.5
    # general linear interp:
    h = (np.arange(1, n+1) - 0.5)/n
    return np.interp(q, h, x)
print('np hazen q0.9 of 1..10:', np.quantile(x, 0.9, method='hazen'), 'formula:', hazen(x, 0.9))
x2 = np.array([1.,2.,3.,4.])
print('np hazen q0.9 of 1..4:', np.quantile(x2, 0.9, method='hazen'), 'formula:', hazen(x2, 0.9))
print('nanquantile supports method:', np.nanquantile(x2, 0.9, method='hazen'))
