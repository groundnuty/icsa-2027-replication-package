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

# verify a full pool percentile/mean directly from raw data for several (doy, cell)
tests = [(200,(30,30)), (153,(0,0)), (244,(59,59)), (1,(15,15)), (366,(45,45)), (59,(25,20)), (61,(25,20))]
for d, (i, j) in tests:
    gi, gj = lat_idx[i], lon_idx[j]
    vals = []
    for y in range(1992, 2003):
        d0 = date_of_doy(d, y)
        s, e = d0 - np.timedelta64(5,'D'), d0 + np.timedelta64(5,'D')
        i0 = np.searchsorted(ext_dates, s); i1 = np.searchsorted(ext_dates, e, side='right')
        for k in range(i0, i1):
            v = ds.analysed_sst.values[b0+k, gi, gj]
            if np.isfinite(v): vals.append(float(v))
    vals = np.array(vals)
    q = np.percentile(vals, 90, method='hazen')
    mn = vals.mean()
    print(f'doy {d:3d} cell({i},{j}): n={len(vals):4d} thr {q:.6f} vs saved {thr[d-1,i,j]:.6f} | mean {mn:.6f} vs saved {clim[d-1,i,j]:.6f}',
          'OK' if (abs(q-thr[d-1,i,j])<1e-9 and abs(mn-clim[d-1,i,j])<1e-9) else 'MISMATCH')

# verify day-60 fill: recompute pools for day 59 and 61 fresh, compare with stored day 60
res = {}
for d in (59, 61):
    out = np.empty((60,60))
    vals_all = []
    for y in range(1992, 2003):
        d0 = date_of_doy(d, y)
        s, e = d0 - np.timedelta64(5,'D'), d0 + np.timedelta64(5,'D')
        i0 = np.searchsorted(ext_dates, s); i1 = np.searchsorted(ext_dates, e, side='right')
        vals_all.append(ds.analysed_sst.values[b0+i0:b0+i1][:, lat_idx][:, :, lon_idx].astype(np.float64))
    v = np.concatenate(vals_all, axis=0)
    out = np.nanpercentile(v, 90, axis=0, method='hazen')
    res[d] = out
print('day60 == mean(day59, day61):', np.allclose(thr[59], 0.5*(res[59]+res[61]), atol=1e-9))