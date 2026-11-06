import numpy as np, xarray as xr

ds = xr.open_dataset('/work/s2z/sst_s2.nc', engine='h5netcdf')
t = ds.time.values
z = np.load('/work/thr_clim.npz')
thr, clim = z['thr'], z['clim']
lat_idx = np.where((ds.latitude.values >= 56.09) & (ds.latitude.values <= 57.29))[0]
lon_idx = np.where((ds.longitude.values >= 10.55) & (ds.longitude.values <= 11.75))[0]
b0 = int(z['b0']); b1 = int(z['b1'])
ext_dates = t[b0:b1].astype('datetime64[D]')

cum = np.array([0,31,60,91,121,152,182,213,244,274,305,335])
def date_of_doy(d, y):
    m = np.searchsorted(cum, d, side='left') - 1
    return np.datetime64(f'{y:04d}-{m+1:02d}-{d-cum[m]:02d}')

def pool_values(d, i, j):
    gi, gj = lat_idx[i], lon_idx[j]
    vals = []
    for y in range(1992, 2003):
        d0 = date_of_doy(d, y)
        s, e = d0 - np.timedelta64(5,'D'), d0 + np.timedelta64(5,'D')
        i0 = np.searchsorted(ext_dates, s); i1 = np.searchsorted(ext_dates, e, side='right')
        v = ds.analysed_sst.isel(time=slice(b0+i0, b0+i1), latitude=int(gi), longitude=int(gj)).values
        vals.append(v.astype(np.float64))
    return np.concatenate(vals)

tests = [(200,(30,30)), (153,(0,0)), (244,(59,59)), (1,(15,15)), (366,(45,45)), (59,(25,20)), (61,(25,20)), (137,(33,44))]
for d, (i, j) in tests:
    vals = pool_values(d, i, j)
    vals = vals[np.isfinite(vals)]
    q = np.percentile(vals, 90, method='hazen'); mn = vals.mean()
    print(f'doy {d:3d} cell({i:2d},{j:2d}): n={len(vals):4d} thr {q:.6f} vs {thr[d-1,i,j]:.6f} | mean {mn:.6f} vs {clim[d-1,i,j]:.6f}',
          'OK' if (abs(q-thr[d-1,i,j])<1e-9 and abs(mn-clim[d-1,i,j])<1e-9) else 'MISMATCH')

# day-60 fill check: recompute day 59 and 61 pools fresh for one cell and compare with stored day 60
r59 = pool_values(59, 30, 30); r61 = pool_values(61, 30, 30)
q59 = np.percentile(r59[np.isfinite(r59)], 90, method='hazen')
q61 = np.percentile(r61[np.isfinite(r61)], 90, method='hazen')
print('day60 vs mean(day59,61) at cell(30,30):', thr[59,30,30], 'vs', 0.5*(q59+q61),
      'OK' if abs(thr[59,30,30]-0.5*(q59+q61))<1e-9 else 'MISMATCH')