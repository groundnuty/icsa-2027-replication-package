import warnings, time, numpy as np, xarray as xr
warnings.filterwarnings('ignore')
path='/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds=xr.open_dataset(path, engine='h5netcdf')
sst=ds['analysed_sst']; latv=ds['latitude']; lonv=ds['longitude']
print("analysed_sst enc:", {k: sst.encoding.get(k) for k in ('dtype','_FillValue','scale_factor','add_offset','chunksizes')},
      "| attrs:", {k: sst.attrs.get(k) for k in ('units','standard_name','long_name')})
print("lat attr: units=%s standard_name=%s" % (latv.attrs.get('units'), latv.attrs.get('standard_name')))
print("lon attr: units=%s standard_name=%s" % (lonv.attrs.get('units'), lonv.attrs.get('standard_name')))

t=ds['time'].values; td=t.astype('datetime64[D]')
lat=latv.values.astype('float64'); lon=lonv.values.astype('float64')
print("lat:", lat[0], "->", lat[-1], "n=", lat.size, "| lon:", lon[0], "->", lon[-1], "n=", lon.size)

def cnt(a,b): return int(((td>=np.datetime64(a))&(td<=np.datetime64(b))).sum())
print("core baseline 1992-2002:", cnt('1992-01-01','2002-12-31'), "(expect 4018)")
print("ext 1991-12-27..31:", cnt('1991-12-27','1991-12-31'), "/5 ; 2003-01-01..05:", cnt('2003-01-01','2003-01-05'), "/5")
print("target 2008-06-01..08-31:", cnt('2008-06-01','2008-08-31'), "(expect 92)")
sl=(td>=np.datetime64('1991-12-27'))&(td<=np.datetime64('2003-01-05'))
d=td[sl].astype(int); print("baseline-ext count:", d.size, "| diffs:", np.unique(np.diff(d)))
st=(td>=np.datetime64('2008-06-01'))&(td<=np.datetime64('2008-08-31'))
dtv=td[st].astype(int); print("target count:", dtv.size, "| diffs:", np.unique(np.diff(dtv)), "| first/last:", td[st][0], td[st][-1])

ilat=np.flatnonzero((lat>=56.63-1e-6)&(lat<=57.83+1e-6))
ilon=np.flatnonzero((lon>=20.23-1e-6)&(lon<=21.43+1e-6))
print("ilat:", ilat[0],"..",ilat[-1],"n=",ilat.size,"contig:",bool(np.all(np.diff(ilat)==1)), "vals:", lat[ilat[0]], lat[ilat[-1]])
print("ilon:", ilon[0],"..",ilon[-1],"n=",ilon.size,"contig:",bool(np.all(np.diff(ilon)==1)), "vals:", lon[ilon[0]], lon[ilon[-1]])

t0=time.time()
it0=int(np.flatnonzero(td==np.datetime64('2008-06-01'))[0])
arr=np.asarray(sst.isel(time=it0, latitude=slice(ilat[0],ilat[-1]+1), longitude=slice(ilon[0],ilon[-1]+1)).values, dtype='float64')
print("read 1 target day: %.2fs | shape" % (time.time()-t0), arr.shape)
print("2008-06-01: finite frac %.4f | min %.4f max %.4f" % (np.isfinite(arr).mean(), np.nanmin(arr), np.nanmax(arr)))
t0=time.time()
ib0=int(np.flatnonzero(td==np.datetime64('1992-06-01'))[0])
arr2=np.asarray(sst.isel(time=ib0, latitude=slice(ilat[0],ilat[-1]+1), longitude=slice(ilon[0],ilon[-1]+1)).values, dtype='float64')
print("read 1 baseline day: %.2fs" % (time.time()-t0))
print("1992-06-01: finite frac %.4f | min %.4f max %.4f" % (np.isfinite(arr2).mean(), np.nanmin(arr2), np.nanmax(arr2)))
np.save('/tmp/latlon.npy', np.array([ilat[0], ilat[-1], ilon[0], ilon[-1]]))
print("numpy:", np.__version__)
try:
    q=np.percentile(np.arange(10)/9, 90, method='hazen'); print("hazen OK:", float(q))
except TypeError as e:
    print("no hazen:", e)
