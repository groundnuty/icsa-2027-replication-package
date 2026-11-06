import numpy as np, xarray as xr, json
p='/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds = xr.open_dataset(p, engine='h5netcdf')
v = ds['analysed_sst']
print('dtype', v.dtype, 'attrs', v.attrs)
print('encoding', {k:val for k,val in v.encoding.items() if k in ('_FillValue','scale_factor','add_offset','dtype','chunksizes','source')})
print('dims', v.dims, 'shape', v.shape)
lat = ds['latitude'].values.astype(np.float64)
lon = ds['longitude'].values.astype(np.float64)
print('lat[0:3]', lat[:3], 'lat[-3:]', lat[-3:])
print('lon[0:3]', lon[:3], 'lon[-3:]', lon[-3:])
latmin, latmax, lonmin, lonmax = 64.51, 65.71, 21.97, 23.17
ilat = np.flatnonzero((lat >= latmin) & (lat <= latmax))
ilon = np.flatnonzero((lon >= lonmin) & (lon <= lonmax))
print('nlat region', ilat.size, ilat[0], ilat[-1], lat[ilat[0]], lat[ilat[-1]])
print('nlon region', ilon.size, ilon[0], ilon[-1], lon[ilon[0]], lon[ilon[-1]])
# check near-boundary values to ensure no float32 surprises
print('lat around bounds:', lat[ilat[0]-1], lat[ilat[0]], lat[ilat[-1]], lat[ilat[-1]+1])
print('lon around bounds:', lon[ilon[0]-1], lon[ilon[0]], lon[ilon[-1]], lon[ilon[-1]+1])
# time indices for target and baseline+extension windows
t = ds['time'].values.astype('datetime64[D]')
def tidx(a, b):
    i0 = np.searchsorted(t, np.datetime64(a)); i1 = np.searchsorted(t, np.datetime64(b), side='right')
    return i0, i1, i1-i0
for a,b in [('2019-06-01','2019-08-31'), ('1991-12-27','2003-01-05'), ('1992-01-01','2002-12-31')]:
    print(a,b,tidx(a,b))
print('time exact daily, count', t.size, t[0], t[-1])
