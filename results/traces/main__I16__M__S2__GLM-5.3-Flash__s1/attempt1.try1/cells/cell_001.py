import warnings, time, numpy as np, xarray as xr
warnings.filterwarnings('ignore')
path='/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds=xr.open_dataset(path, engine='h5netcdf')
print("sizes:", dict(ds.sizes))
print("vars:")
for v in list(ds.variables):
    print("  ", v, ds[v].dtype, ds[v].shape)
t=ds['time'].values
print("time dtype:", t.dtype, "| n:", t.size, "| first:", t[0], "| last:", t[-1])
print("time enc:", {k: ds['time'].encoding.get(k) for k in ('units','calendar','dtype')})
lat=ds['lat'].values; lon=ds['lon'].values
print("lat:", lat.dtype, lat[0], "->", lat[-1], "n=", lat.size)
print("lon:", lon.dtype, lon[0], "->", lon[-1], "n=", lon.size)
for v in ds.variables:
    if v in ('time','lat','lon','latitude','longitude'): continue
    e=ds[v].encoding
    print(v, "enc:", {k:e.get(k) for k in ('dtype','_FillValue','scale_factor','add_offset','chunksizes')},
          "| units:", ds[v].attrs.get('units'), "| std_name:", ds[v].attrs.get('standard_name'))
print("globals:", {k: ds.attrs[k] for k in list(ds.attrs)[:8]})

td=t.astype('datetime64[D]')
def cnt(a,b): return int(((td>=np.datetime64(a))&(td<=np.datetime64(b))).sum())
print("core baseline 1992-2002 days present:", cnt('1992-01-01','2002-12-31'), "expected 4018")
print("ext 1991-12-27..31 present:", cnt('1991-12-27','1991-12-31'), "/5 ; 2003-01-01..05 present:", cnt('2003-01-01','2003-01-05'), "/5")
print("target 2008-06-01..08-31 present:", cnt('2008-06-01','2008-08-31'), "expected 92")
sl=(td>=np.datetime64('1991-12-27'))&(td<=np.datetime64('2003-01-05'))
d=td[sl].astype(int)
print("baseline-ext slice count:", d.size, "| diff values:", np.unique(np.diff(d)) if d.size>1 else "-")
st=(td>=np.datetime64('2008-06-01'))&(td<=np.datetime64('2008-08-31'))
dtv=td[st].astype(int)
print("target slice count:", dtv.size, "| first/last:", td[st][0], td[st][-1], "| diffs:", np.unique(np.diff(dtv)) if dtv.size>1 else "-")

lat64=lat.astype('float64'); lon64=lon.astype('float64')
ilat=np.flatnonzero((lat64>=56.63-1e-6)&(lat64<=57.83+1e-6))
ilon=np.flatnonzero((lon64>=20.23-1e-6)&(lon64<=21.43+1e-6))
print("ilat:", ilat[0], "..", ilat[-1], "n=", ilat.size, "contig:", bool(np.all(np.diff(ilat)==1)))
print("ilon:", ilon[0], "..", ilon[-1], "n=", ilon.size, "contig:", bool(np.all(np.diff(ilon)==1)))
print("lat used:", lat64[ilat[0]], "..", lat64[ilat[-1]], "| lon used:", lon64[ilon[0]], "..", lon64[ilon[-1]])

t0=time.time()
it0=int(np.flatnonzero(td==np.datetime64('2008-06-01'))[0])
arr=np.asarray(ds['sst'].isel(time=it0, lat=slice(ilat[0],ilat[-1]+1), lon=slice(ilon[0],ilon[-1]+1)).values, dtype='float64')
print("read 1 target day: %.2fs" % (time.time()-t0))
print("2008-06-01 sample: shape", arr.shape, "finite frac:", round(float(np.isfinite(arr).mean()),4),
      "min/max:", float(np.nanmin(arr)), float(np.nanmax(arr)))
has=(td==np.datetime64('1992-06-01')).any()
if has:
    ib0=int(np.flatnonzero(td==np.datetime64('1992-06-01'))[0])
    t0=time.time()
    arr2=np.asarray(ds['sst'].isel(time=ib0, lat=slice(ilat[0],ilat[-1]+1), lon=slice(ilon[0],ilon[-1]+1)).values, dtype='float64')
    print("read 1 baseline day: %.2fs" % (time.time()-t0))
    print("1992-06-01 sample: finite frac:", round(float(np.isfinite(arr2).mean()),4),
          "min/max:", float(np.nanmin(arr2)), float(np.nanmax(arr2)))
print("numpy:", np.__version__)
try:
    x=np.random.RandomState(0).rand(50); q=np.percentile(x,90,method='hazen'); print("hazen kwarg OK:", float(q))
except TypeError as e:
    print("no hazen kwarg:", e)
