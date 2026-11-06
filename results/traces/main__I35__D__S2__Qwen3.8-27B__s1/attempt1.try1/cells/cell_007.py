import xarray as xr, numpy as np, pickle

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
lat = ds['latitude'].values; lon = ds['longitude'].values
eps = 1e-4
lat_sel = (lat >= 59.93 - eps) & (lat <= 61.13 + eps)
lon_sel = (lon >= 18.69 - eps) & (lon <= 19.89 + eps)
j0 = int(np.nonzero(lat_sel)[0][0]); j1 = int(np.nonzero(lat_sel)[0][-1])
k0 = int(np.nonzero(lon_sel)[0][0]); k1 = int(np.nonzero(lon_sel)[0][-1])
assert lat_sel[j0:j1+1].all() and lon_sel[k0:k1+1].all()

t = ds['time'].values
i_ext0 = int(np.searchsorted(t, np.datetime64('1991-12-27')))
i_ext1 = int(np.searchsorted(t, np.datetime64('2003-01-05')))
i_t0   = int(np.searchsorted(t, np.datetime64('2009-06-01')))
i_t1   = int(np.searchsorted(t, np.datetime64('2009-08-31')))
i_b0   = int(np.searchsorted(t, np.datetime64('1992-01-01')))
i_b1   = int(np.searchsorted(t, np.datetime64('2002-12-31')))

# load SST for region slices (float64)
S_ext = ds['analysed_sst'].isel(time=slice(i_ext0, i_ext1+1), latitude=slice(j0, j1+1), longitude=slice(k0, k1+1)).values.astype(np.float64)
S_tgt = ds['analysed_sst'].isel(time=slice(i_t0, i_t1+1), latitude=slice(j0, j1+1), longitude=slice(k0, k1+1)).values.astype(np.float64)
print('S_ext', S_ext.shape, 'NaNs:', int(np.isnan(S_ext).sum()), 'of', S_ext.size)
print('S_tgt', S_tgt.shape, 'NaNs:', int(np.isnan(S_tgt).sum()), 'of', S_tgt.size)
print('S_ext range (finite):', np.nanmin(S_ext), np.nanmax(S_ext))
print('S_tgt range (finite):', np.nanmin(S_tgt), np.nanmax(S_tgt))

# day-of-year by (month, day) in leap-year calendar: 1..366
def doy_leap(tarr):
    y0 = tarr.astype('datetime64[Y]')
    m0 = tarr.astype('datetime64[M]')
    d_of_m = (tarr - m0).astype('timedelta64[D]').astype('int64') + 1
    m_of_y = (m0.astype('datetime64[D]') - y0.astype('datetime64[D]')).astype('timedelta64[D]').astype('int64') + 1
    cum = np.array([0,31,60,91,121,152,182,213,244,274,305,335])  # leap-year days before month m (m=1..12)
    return (cum[m_of_y-1] + d_of_m).astype(np.int64)

t_ext = t[i_ext0:i_ext1+1]
t_tgt = t[i_t0:i_t1+1]
doy_ext = doy_leap(t_ext)
doy_tgt = doy_leap(t_tgt)
# sanity: unique doy in ext should be 1..366 (1992..2002 contains leap years)
print('doy_ext unique count:', np.unique(doy_ext).size, 'min/max:', doy_ext.min(), doy_ext.max())
print('doy_tgt range:', doy_tgt.min(), doy_tgt.max())

# pool matrix M[day 1..366, ext-day]: M[d-1, c] iff ext-day c within +/-5 cal days of a baseline date with doy d
M = np.zeros((366, i_ext1 - i_ext0 + 1), dtype=bool)
base = np.arange(i_b0 - i_ext0, i_b1 - i_ext0 + 1)  # ext-local idx of baseline dates
doy_base = doy_ext[base]
for kk in range(-5, 6):
    col = base + kk
    ok = (col >= 0) & (col < M.shape[1])
    col = col[ok]; rows = doy_base[ok]
    keep = rows != 60
    M[rows[keep]-1, col[keep]] = True
print('pool sizes: min', M.sum(axis=1).min(), 'max', M.sum(axis=1).max())
print('pool size per doy (first 5):', M.sum(axis=1)[:5], 'day59,61:', M[58].sum(), M[60].sum())

import pickle
with open('/work/step1.pkl','wb') as f:
    pickle.dump(dict(S_ext=S_ext, S_tgt=S_tgt, t_ext=t_ext, t_tgt=t_tgt,
                     doy_ext=doy_ext, doy_tgt=doy_tgt, M=M,
                     lat=lat[j0:j1+1], lon=lon[k0:k1+1], t_tgt_full=t_tgt), f)
print('saved step1')
