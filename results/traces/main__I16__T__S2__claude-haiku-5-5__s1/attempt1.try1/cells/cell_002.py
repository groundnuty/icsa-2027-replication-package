
lat=ds.latitude.values; lon=ds.longitude.values
la=np.where((lat>=56.63)&(lat<=57.83))[0]; lo=np.where((lon>=20.23)&(lon<=21.43))[0]
print(len(la),len(lo), lat[la[0]],lat[la[-1]],lon[lo[0]],lon[lo[-1]])
sub=ds.isel(latitude=slice(la[0],la[-1]+1),longitude=slice(lo[0],lo[-1]+1))
b=sub.analysed_sst.sel(time=slice('1991-12-27','2003-01-05')).load()
t=sub.analysed_sst.sel(time=slice('2008-06-01','2008-08-31')).load()
print(b.shape,t.shape, np.isnan(b.values).mean(), np.isnan(t.values).mean())
