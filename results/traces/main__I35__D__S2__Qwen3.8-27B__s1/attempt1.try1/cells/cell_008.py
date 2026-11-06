import xarray as xr, numpy as np, pickle

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
lat = ds['latitude'].values; lon = ds['longitude'].values
eps = 1e-4
lat_sel = (lat >= 59.93 - eps) & (lat <= 61.13 + eps)
lon_sel = (lon >= 18.69 - eps) & (lon <= 19.89 + eps)
j0 = int(np.nonzero(lat_sel)[0][0]); j1 = int(np.nonzero(lat_sel)[0][-1])
k0 = int(np.nonzero(lon_sel)[0][0]); k1 = int(np.nonzero(lon_sel)[0][-1])
t = ds['time'].values
i_ext0 = int(np.searchsorted(t, np.datetime64('1991-12-27'))); i_ext1 = int(np.searchsorted(t, np.datetime64('2003-01-05')))
i_t0   = int(np.searchsorted(t, np.datetime64('2009-06-01')));     i_t1   = int(np.searchsorted(t, np.datetime64('2009-08-31')))
i_b0   = int(np.searchsorted(t, np.datetime64('1992-01-01')));     i_b1   = int(np.searchsorted(t, np.datetime64('2002-12-31')))

def doy_leap(tarr):
    ti = tarr.astype('datetime64[D]').astype('int64')
    ms = tarr.astype('datetime64[M]').astype('datetime64[D]').astype('int64')
    ys = tarr.astype('datetime64[Y]').astype('datetime64[D]').astype('int64')
    d_of_m = ti - ms + 1                                   # day of month
    off = ms - ys                                          # day-of-year (0-based) of month start, actual calendar
    month = np.searchsorted(np.array([0,31,59,90,120,151,181,212,243,273,304,334]), off, side='right')
    cum = np.array([0,31,60,91,121,152,182,213,244,274,305,335])  # leap-year days before month
    return (cum[month-1] + d_of_m).astype(np.int64)

t_ext = t[i_ext0:i_ext1+1]; t_tgt = t[i_t0:i_t1+1]
doy_ext = doy_leap(t_ext); doy_tgt = doy_leap(t_tgt)
print('doy_ext uniques:', np.unique(doy_ext).size, 'min/max:', doy_ext.min(), doy_ext.max())
# explicit checks
def doy_of(s): 
    return doy_leap(np.array([np.datetime64(s)]))[0]
print('1993-03-01:', doy_of('1993-03-01'), '| 2000-02-29:', doy_of('2000-02-29'), '| 2001-02-28:', doy_of('2001-02-28'),
      '| 2009-06-01:', doy_of('2009-06-01'), '| 2009-08-31:', doy_of('2009-08-31'), '| 2009-01-01:', doy_of('2009-01-01'))
print('doy_tgt min/max:', doy_tgt.min(), doy_tgt.max())

S_ext = ds['analysed_sst'].isel(time=slice(i_ext0, i_ext1+1), latitude=slice(j0, j1+1), longitude=slice(k0, k1+1)).values.astype(np.float64)
S_tgt = ds['analysed_sst'].isel(time=slice(i_t0, i_t1+1), latitude=slice(j0, j1+1), longitude=slice(k0, k1+1)).values.astype(np.float64)
print('S_ext', S_ext.shape, 'NaNs:', int(np.isnan(S_ext).sum()))
print('S_tgt', S_tgt.shape, 'NaNs:', int(np.isnan(S_tgt).sum()))

M = np.zeros((366, i_ext1 - i_ext0 + 1), dtype=bool)
base = np.arange(i_b0 - i_ext0, i_b1 - i_ext0 + 1)
doy_base = doy_ext[base]
for kk in range(-5, 6):
    col = base + kk
    ok = (col >= 0) & (col < M.shape[1])
    col = col[ok]; rows = doy_base[ok]
    keep = rows != 60
    M[rows[keep]-1, col[keep]] = True
ps = M.sum(axis=1)
print('pool sizes: min', ps.min(), 'max', ps.max(), '| day1:', ps[0], 'day59:', ps[58], 'day61:', ps[60], 'day366:', ps[365])

# verify a pool manually: day 1 (Jan 1) anchors 1992-01-01..2002-01-01, windows +-5
cols = np.flatnonzero(M[0])
ext_dates = t_ext[cols]
print('day1 pool: n=', len(cols), 'first:', ext_dates[0], 'last:', ext_dates[-1])
# should span 1991-12-27 .. 2002-01-06
print('day366 pool last:', t_ext[np.flatnonzero(M[365])][-1])
print('day59 pool includes 1992-02-29?', np.any(t_ext[np.flatnonzero(M[58])] == np.datetime64('1992-02-29')))
print('day61 pool includes 1996-02-29?', np.any(t_ext[np.flatnonzero(M[60])] == np.datetime64('1996-02-29')))

with open('/work/step1.pkl','wb') as f:
    pickle.dump(dict(S_ext=S_ext, S_tgt=S_tgt, t_ext=t_ext, t_tgt=t_tgt,
                     doy_ext=doy_ext, doy_tgt=doy_tgt, M=M,
                     lat=lat[j0:j1+1], lon=lon[k0:k1+1]), f)
print('saved step1')
