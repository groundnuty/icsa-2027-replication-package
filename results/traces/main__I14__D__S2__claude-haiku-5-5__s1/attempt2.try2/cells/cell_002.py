
v=ds.analysed_sst
print(v.attrs, v.encoding.get('scale_factor'), v.encoding.get('dtype'))
sub = ds.sel(latitude=slice(56.0,57.5), longitude=slice(17.6,19.0))
print(sub.latitude.values[[0,-1]], sub.longitude.values[[0,-1]], sub.sizes)
la=sub.latitude.values; lo=sub.longitude.values
print(la[(la>=56.13)&(la<=57.33)][[0,-1]], lo[(lo>=17.71)&(lo<=18.91)][[0,-1]])
