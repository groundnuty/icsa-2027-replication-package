
print(ds.analysed_sst.attrs); print(ds.attrs['comment'])
lat=ds.latitude.values; lon=ds.longitude.values
la=np.where((lat>=56.09)&(lat<=57.29))[0]; lo=np.where((lon>=10.55)&(lon<=11.75))[0]
print(len(la),len(lo), lat[la[[0,-1]]], lon[lo[[0,-1]]])
sub = ds.analysed_sst.isel(latitude=slice(la[0],la[-1]+1), longitude=slice(lo[0],lo[-1]+1))
sub = sub.sel(time=slice('1991-12-27','2009-08-31')).load()
print(sub.shape, np.isnan(sub.values).sum(), np.nanmin(sub.values), np.nanmax(sub.values))
